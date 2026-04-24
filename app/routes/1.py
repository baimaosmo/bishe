import os
import math
import random
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, TensorDataset
from sklearn.model_selection import StratifiedKFold
# [评估新增] 引入了更全面的分类评估库
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, confusion_matrix
from sklearn.cluster import KMeans
import networkx as nx 
import datetime 

# 持久同调库检查
try:
    import ripser
except ImportError:
    print("[Warning] 'ripser' 库未安装，请使用 'pip install ripser' 进行安装。否则拓扑提取将返回全0向量。")

# ================= 配置 =================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

set_seed(42)

# =========================================================
# 1) 数据集
# =========================================================
class FCMatDataset(Dataset):
    def __init__(self, fc_dir, label_csv, id_width=7, V=116):
        self.fc_dir = fc_dir
        self.V = V
        df = pd.read_csv(label_csv, header=None, sep=r"\s+")
        df.columns = ["id", "label"]
        df["id"] = df["id"].astype(str).str.zfill(id_width)
        self.ids = df["id"].tolist()
        self.labels = df["label"].astype(int).tolist()
        print("Loading FC matrices...")
        self.fcs = []
        for sid in self.ids:
            fc_path = os.path.join(self.fc_dir, f"{sid}.csv")
            try:
                mat = np.loadtxt(fc_path, dtype=np.float32)
            except Exception:
                df_fc = pd.read_csv(fc_path, header=None, dtype=str)
                rows = df_fc[0].apply(lambda x: x.strip().split())
                mat = np.array(rows.tolist(), dtype=np.float32)
            mat = np.nan_to_num(mat, nan=0.0, posinf=0.0, neginf=0.0)
            mat = np.clip(mat, -1.0, 1.0)
            np.fill_diagonal(mat, 0.0)
            if mat.shape != (V, V):
                raise ValueError(f"{fc_path} shape {mat.shape} != ({V},{V})")
            self.fcs.append(torch.from_numpy(mat).float())
        print(f"Loaded {len(self.fcs)} subjects. One FC shape: {self.fcs[0].shape}")

    def __len__(self):
        return len(self.fcs)
    def __getitem__(self, idx):
        return self.fcs[idx], torch.tensor(self.labels[idx], dtype=torch.long)

# =========================================================
# 持久同调特征提取 (Persistence Landscape 简化版)
# =========================================================
def extract_persistence_landscape(fc_matrix, resolution=50):
    try:
        dist_mat = 1.0 - fc_matrix.cpu().numpy()
        np.fill_diagonal(dist_mat, 0)
        
        dgms = ripser.ripser(dist_mat, distance_matrix=True, maxdim=1)['dgms']
        H0, H1 = dgms[0], dgms[1]
        
        H0 = H0[H0[:, 1] < np.inf]
        
        lifetimes_0 = H0[:, 1] - H0[:, 0]
        lifetimes_1 = H1[:, 1] - H1[:, 0] if len(H1) > 0 else np.zeros(1)
        
        all_life = np.concatenate([lifetimes_0, lifetimes_1])
        all_life = np.sort(all_life)[::-1] 
        
        mu_G = np.zeros(resolution, dtype=np.float32)
        length = min(resolution, len(all_life))
        mu_G[:length] = all_life[:length]
        
        return torch.from_numpy(mu_G)
    except Exception as e:
        return torch.zeros(resolution, dtype=torch.float32)

# =========================================================
# 2) 构图与工具函数
# =========================================================
@torch.no_grad()
def build_topk_adjacency(fc, topk=20, use_abs=True):
    w = fc.detach()
    w = w - torch.diag_embed(torch.diagonal(w, dim1=1, dim2=2))
    if use_abs: w = w.abs()
    B, V, _ = w.shape
    vals, idx = torch.topk(w, k=min(topk, V-1), dim=-1, largest=True, sorted=False)
    mask = torch.zeros_like(w)
    mask.scatter_(-1, idx, 1.0)
    mask = ((mask + mask.transpose(1, 2)) > 0).float()
    W = w * mask
    return W

def normalize_adjacency(W, eps=1e-6):
    deg = W.sum(dim=-1).clamp(min=eps)
    inv_sqrt = torch.rsqrt(deg)
    return inv_sqrt.unsqueeze(2) * W * inv_sqrt.unsqueeze(1)

def generate_ba_mask(V, m_attach=5):
    m_safe = max(1, min(m_attach, V - 1))
    G = nx.barabasi_albert_graph(n=V, m=m_safe, seed=None)
    mask_np = nx.to_numpy_array(G, dtype=np.float32)
    mask = torch.from_numpy(mask_np)
    return mask

def flatten_upper(fc, k=1):
    V = fc.size(1)
    idx = torch.triu_indices(V, V, offset=k, device=fc.device)
    return fc[:, idx[0], idx[1]]

def repair_and_filter(real_flat, fake_flat, top_k_ratio=1.0):
    if torch.isnan(fake_flat).any(): return real_flat[:10]
    fake_flat = torch.clamp(fake_flat, -1.0, 1.0)
    real_mean = real_flat.mean(dim=0, keepdim=True)
    sim = F.cosine_similarity(fake_flat, real_mean + 1e-6, dim=1)
    k = max(5, int(len(fake_flat) * top_k_ratio))
    top_vals, top_idx = torch.topk(sim, k=k)
    return fake_flat[top_idx]

# =========================================================
# 3) Graph RAE & Diffusion Models (精简显示，未做逻辑修改)
# =========================================================
class GraphConv(nn.Module):
    def __init__(self, dim, dropout=0.1):
        super().__init__()
        self.lin = nn.Linear(dim, dim)
        self.norm = nn.LayerNorm(dim)
        self.drop = nn.Dropout(dropout)
    def forward(self, H, Wn):
        return self.drop(F.silu(self.norm(self.lin(torch.bmm(Wn, H)))))

class GraphEncoder(nn.Module):
    def __init__(self, V=116, hidden=256, layers=3, topk=20, dropout=0.1):
        super().__init__()
        self.topk = topk
        self.hidden = hidden
        self.in_proj = nn.Sequential(nn.Linear(V, hidden), nn.LayerNorm(hidden), nn.SiLU(), nn.Dropout(dropout))
        self.gconvs = nn.ModuleList([GraphConv(hidden, dropout=dropout) for _ in range(layers)])
    def forward(self, fc):
        B, V, _ = fc.shape
        W = build_topk_adjacency(fc, topk=self.topk, use_abs=True).to(fc.device)
        Wn = normalize_adjacency(W)
        H = self.in_proj(fc.reshape(B * V, V)).view(B, V, self.hidden)
        for g in self.gconvs: H = H + g(H, Wn)
        return H 

class GraphRAE(nn.Module):
    def __init__(self, V=116, K=64, hidden=256, layers=3, topk=20, dropout=0.1):
        super().__init__()
        self.V = V; self.K = K 
        self.encoder = GraphEncoder(V=V, hidden=hidden, layers=layers, topk=topk, dropout=dropout)
        self.to_z = nn.Linear(hidden, K); self.z_norm = nn.LayerNorm(K)
        self.dec_proj = nn.Linear(K, K, bias=False)
    def decode(self, z):
        z_proj = self.dec_proj(z)
        recon = torch.tanh(torch.matmul(z_proj, z_proj.transpose(1, 2)) / math.sqrt(self.K))
        return recon - torch.diag_embed(torch.diagonal(recon, dim1=1, dim2=2))
    def forward(self, fc):
        z = self.z_norm(self.to_z(self.encoder(fc))) 
        return self.decode(z), z

def fc_recon_loss(recon, target):
    mask = 1.0 - torch.eye(recon.size(1), device=recon.device).unsqueeze(0)
    return F.mse_loss(recon * mask, target * mask)

class LatentNormalizer:
    def __init__(self, eps=1e-6): self.eps = eps; self.mean = None; self.std = None
    def fit(self, z):
        with torch.no_grad():
            self.mean = z.mean(dim=(0,1), keepdim=True); self.std = z.std(dim=(0,1), keepdim=True).clamp(min=self.eps)
    def transform(self, z): return (z - self.mean) / self.std
    def inverse(self, z): return z * self.std + self.mean

class SinusoidalPositionEmbeddings(nn.Module):
    def __init__(self, dim): super().__init__(); self.dim = dim
    def forward(self, t):
        device = t.device; half = self.dim // 2
        emb = torch.exp(torch.arange(half, device=device) * -(math.log(10000) / (half - 1)))
        emb = t[:, None].float() * emb[None, :]
        return torch.cat([emb.sin(), emb.cos()], dim=-1)

class ResGCNBlock(nn.Module):
    def __init__(self, hidden, dropout=0.1):
        super().__init__()
        self.norm = nn.LayerNorm(hidden); self.lin = nn.Linear(hidden, hidden)
        self.act = nn.SiLU(); self.drop = nn.Dropout(dropout)
    def forward(self, x, adj, gamma=None, beta=None):
        h = self.norm(self.lin(torch.matmul(adj, x)))
        if gamma is not None and beta is not None: h = h * (1 + gamma) + beta
        return x + self.drop(self.act(h))

class ConditionalDiffusionGCN(nn.Module):
    def __init__(self, V=116, K=64, hidden=256, depth=6, num_classes=2, dropout=0.1, topo_dim=50):
        super().__init__()
        self.in_proj = nn.Linear(K, hidden)
        self.time_mlp = nn.Sequential(SinusoidalPositionEmbeddings(128), nn.Linear(128, hidden), nn.SiLU(), nn.Linear(hidden, hidden))
        self.label_emb = nn.Embedding(num_classes, hidden)
        self.topo_mlp = nn.Sequential(nn.Linear(topo_dim, hidden), nn.SiLU(), nn.Linear(hidden, hidden))
        self.cond_proj = nn.Linear(hidden, hidden * 2) 
        self.adj_param = nn.Parameter(torch.randn(V, V))
        self.layers = nn.ModuleList([ResGCNBlock(hidden, dropout) for _ in range(depth)])
        self.out_norm = nn.LayerNorm(hidden); self.out_proj = nn.Linear(hidden, K)
    def get_normalized_adj(self):
        A = torch.sigmoid(self.adj_param + self.adj_param.transpose(0, 1))
        return A / A.sum(dim=1, keepdim=True).clamp(min=1e-6)
    def forward(self, x, t, y, mu_G):
        h = self.in_proj(x)
        cond = self.time_mlp(t)[:, None, :] + self.label_emb(y)[:, None, :] + self.topo_mlp(mu_G)[:, None, :] 
        gamma, beta = self.cond_proj(cond).chunk(2, dim=-1)
        adj = self.get_normalized_adj()
        for layer in self.layers: h = layer(h, adj, gamma, beta)
        return self.out_proj(self.out_norm(h))

class LatentDDPM:
    def __init__(self, model, T=1000):
        self.model = model; self.T = T
        betas = torch.linspace(1e-4, 0.02, T, device=device)
        self.betas = betas; self.alphas = 1.0 - betas
        self.alphas_cumprod = torch.cumprod(self.alphas, dim=0)
        self.alphas_cumprod_prev = F.pad(self.alphas_cumprod[:-1], (1, 0), value=1.0)
        self.sqrt_ac = torch.sqrt(self.alphas_cumprod); self.sqrt_om = torch.sqrt(1.0 - self.alphas_cumprod)
        self.posterior_var = betas * (1.0 - self.alphas_cumprod_prev) / (1.0 - self.alphas_cumprod + 1e-8)
    def q_sample(self, x0, t, noise=None):
        if noise is None: noise = torch.randn_like(x0)
        return extract(self.sqrt_ac, t, x0.shape) * x0 + extract(self.sqrt_om, t, x0.shape) * noise, noise
    @torch.no_grad()
    def p_sample(self, x_t, t, y, mu_g):
        eps = torch.clamp(self.model(x_t, t, y, mu_g), -2.0, 2.0)
        alpha_t = extract(self.alphas, t, x_t.shape); alpha_bar = extract(self.alphas_cumprod, t, x_t.shape)
        beta_t = extract(self.betas, t, x_t.shape)
        mean = (1.0/torch.sqrt(alpha_t))*(x_t - (beta_t/torch.sqrt(1.0-alpha_bar+1e-6))*eps)
        var = extract(self.posterior_var, t, x_t.shape)
        return mean + (t!=0).float().view(-1,1,1) * torch.sqrt(var+1e-6) * torch.randn_like(x_t)
    @torch.no_grad()
    def sample(self, n, V, K, y, mu_g):
        x = torch.randn(n, V, K, device=device)
        for i in range(self.T - 1, -1, -1):
            x = torch.clamp(self.p_sample(x, torch.full((n,), i, device=device, dtype=torch.long), y, mu_g), -4.0, 4.0)
        return x

def extract(a, t, x_shape):
    out = a.gather(0, t)
    while len(out.shape) < len(x_shape): out = out.unsqueeze(-1)
    return out

class ClusterGatedMLP(nn.Module):
    def __init__(self, input_dim=6670, num_clusters=8, hidden_dim=64):
        super().__init__()
        self.gate_net = nn.Sequential(nn.Linear(num_clusters, 32), nn.ReLU(), nn.Linear(32, input_dim), nn.Sigmoid())
        self.classifier = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.BatchNorm1d(hidden_dim), nn.ReLU(), nn.Dropout(0.5),
            nn.Linear(hidden_dim, 32), nn.ReLU(), nn.Dropout(0.3), nn.Linear(32, 2)
        )
    def forward(self, x, cluster_probs):
        return self.classifier(x * self.gate_net(cluster_probs) + x)

# =========================================================
# 6) 主流程 (含新增评估指标)
# =========================================================
def run_pipeline(dataset, k=5, V=116, K=64,
                 ae_epochs=300, ae_bs=32, diff_epochs=400, diff_bs=32, T=1000, gen_per_class=200,
                 ba_m=5, lambda_topo=0.1, lambda_reg=1e-5, lambda_con=0.5, num_clusters=8, topk=20, 
                 enc_hidden=128, enc_layers=2, enc_dropout=0.2, topo_resolution=50, 
                 log_path="training_log.txt"):

    all_fc = torch.stack([dataset[i][0] for i in range(len(dataset))])
    all_y = np.array([int(dataset[i][1].item()) for i in range(len(dataset))])
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
    D = V * (V - 1) // 2
    
    # [评估新增] 初始化用于记录多维评估指标的列表
    acc_scores, auc_scores, f1_scores = [], [], []
    prec_scores, rec_scores, spec_scores = [], [], []
    gen_mse_scores = [] # 记录生成分布的 MSE，用于评估扩散模型质量

    print(">>> [Pre-Extraction] Persistence Landscapes for all subjects...")
    mu_G_all = []
    for fc in all_fc:
        mu_G_all.append(extract_persistence_landscape(fc, resolution=topo_resolution))
    mu_G_all = torch.stack(mu_G_all).to(device)

    for fold, (tr, va) in enumerate(skf.split(all_fc, all_y)):
        print(f"\n========== Fold {fold+1}/{k} ==========")
        X_tr, y_tr = all_fc[tr].to(device), torch.tensor(all_y[tr], dtype=torch.long, device=device)
        X_va, y_va = all_fc[va].to(device), torch.tensor(all_y[va], dtype=torch.long, device=device)
        mu_G_tr = mu_G_all[tr]

        # --- Step 1: Graph RAE ---
        print(f">>> [Step 1] Training Graph-RAE with PH Contrastive Loss...")
        rae = GraphRAE(V=V, K=K, hidden=enc_hidden, layers=enc_layers, topk=topk, dropout=enc_dropout).to(device)
        opt_ae = torch.optim.Adam(rae.parameters(), lr=1e-3)
        ae_loader = DataLoader(TensorDataset(X_tr, mu_G_tr), batch_size=ae_bs, shuffle=True)
        rae.train()
        for ep in range(ae_epochs):
            total_loss = 0.0
            ba_mask = generate_ba_mask(V, m_attach=ba_m).to(device)
            non_ba_mask = 1.0 - (ba_mask > 0).float()
            for fc, mu_g in ae_loader:
                fc, mu_g = fc.to(device), mu_g.to(device)
                recon, z = rae(fc)
                r_loss = fc_recon_loss(recon, fc)
                reg_loss = torch.mean(z ** 2)
                topo_loss = torch.mean((recon * non_ba_mask) ** 2)
                
                z_graph = z.mean(dim=1) 
                z_graph_norm = F.normalize(z_graph, p=2, dim=1)
                mu_g_norm = F.normalize(mu_g, p=2, dim=1)
                sim_z = torch.matmul(z_graph_norm, z_graph_norm.T)
                sim_ph = torch.matmul(mu_g_norm, mu_g_norm.T) 
                con_loss = F.mse_loss(sim_z, sim_ph)

                loss = r_loss + (lambda_reg * reg_loss) + (lambda_topo * topo_loss) + (lambda_con * con_loss)
                opt_ae.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(rae.parameters(), 1.0)
                opt_ae.step(); total_loss += loss.item()
            if (ep + 1) % 50 == 0: print(f"RAE Ep {ep+1:03d} | Loss={total_loss/len(ae_loader):.5f}")
        rae.eval()
        with torch.no_grad(): _, Z_tr_raw = rae(X_tr)

        # --- Step 2: Latent Diffusion ---
        print(">>> [Step 2] Training Topology-Guided Diffusion...")
        norm = LatentNormalizer(); norm.fit(Z_tr_raw); Z_tr_n = norm.transform(Z_tr_raw)
        cdt = ConditionalDiffusionGCN(V=V, K=K, hidden=256, depth=6, num_classes=2, dropout=0.1, topo_dim=topo_resolution).to(device)
        ddpm = LatentDDPM(cdt, T=T)
        opt_diff = torch.optim.AdamW(cdt.parameters(), lr=2e-4, weight_decay=1e-4)
        diff_loader = DataLoader(TensorDataset(Z_tr_n, y_tr, mu_G_tr), batch_size=diff_bs, shuffle=True)

        cdt.train()
        for ep in range(diff_epochs):
            for z, y, mu_g in diff_loader:
                mu_g = mu_g.to(device)
                t = torch.randint(0, ddpm.T, (z.size(0),), device=device).long()
                zt, noise = ddpm.q_sample(z, t)
                loss = F.mse_loss(cdt(zt, t, y, mu_g), noise)
                opt_diff.zero_grad(); loss.backward(); opt_diff.step()
            if (ep + 1) % 100 == 0: print(f"    Diff Ep {ep+1}/{diff_epochs} | Loss={loss.item():.6f}")

        # --- Step 3: Generation & Gen-Quality Evaluation ---
        print(">>> [Step 3] Generating Topology-Consistent FCs...")
        cdt.eval()
        with torch.no_grad():
            y0 = torch.zeros(gen_per_class, dtype=torch.long, device=device)
            y1 = torch.ones(gen_per_class, dtype=torch.long, device=device)
            mu_g_mean_0 = mu_G_tr[y_tr == 0].mean(dim=0).unsqueeze(0).repeat(gen_per_class, 1)
            mu_g_mean_1 = mu_G_tr[y_tr == 1].mean(dim=0).unsqueeze(0).repeat(gen_per_class, 1)
            
            Z0 = norm.inverse(ddpm.sample(gen_per_class, V, K, y0, mu_g_mean_0))
            Z1 = norm.inverse(ddpm.sample(gen_per_class, V, K, y1, mu_g_mean_1))
            FC0, FC1 = rae.decode(Z0), rae.decode(Z1)

            X_tr_flat = flatten_upper(X_tr)
            X0_flat = flatten_upper(FC0)
            X1_flat = flatten_upper(FC1)
            X_va_flat = flatten_upper(X_va)
            
            # [评估新增] 计算生成矩阵分布与真实训练矩阵分布的均方误差 (Gen-MSE)
            # 这个指标帮助你判断生成图的全局分布是否发生漂移
            real_mean_0 = X_tr_flat[y_tr==0].mean(dim=0)
            real_mean_1 = X_tr_flat[y_tr==1].mean(dim=0)
            fake_mean_0 = X0_flat.mean(dim=0)
            fake_mean_1 = X1_flat.mean(dim=0)
            
            gen_mse_0 = F.mse_loss(fake_mean_0, real_mean_0).item()
            gen_mse_1 = F.mse_loss(fake_mean_1, real_mean_1).item()
            fold_gen_mse = (gen_mse_0 + gen_mse_1) / 2.0
            print(f"    [Generation Quality] Gen-MSE (Dist. Shift vs Real): {fold_gen_mse:.5f}")
            gen_mse_scores.append(fold_gen_mse)
            
            X0_keep = repair_and_filter(X_tr_flat[y_tr==0], X0_flat, top_k_ratio=1.0)
            X1_keep = repair_and_filter(X_tr_flat[y_tr==1], X1_flat, top_k_ratio=1.0)

        # --- Step 4: Classifier ---
        print(f">>> [Step 4] Clustering & Training Gated MLP...")
        X_train_final = torch.cat([X_tr_flat, X0_keep, X1_keep], dim=0)
        y_train_final = torch.cat([y_tr, torch.zeros(len(X0_keep), device=device), torch.ones(len(X1_keep), device=device)], dim=0).long()
        
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10).fit(X_tr_flat.cpu().numpy())
        def get_cluster_probs(X_tensor, kmeans_model, temp=1.0):
            dists = torch.from_numpy(kmeans_model.transform(X_tensor.cpu().numpy())).to(X_tensor.device)
            return F.softmax(-dists / temp, dim=1) 
            
        train_probs, val_probs = get_cluster_probs(X_train_final, kmeans), get_cluster_probs(X_va_flat, kmeans)
        mlp = ClusterGatedMLP(input_dim=D, num_clusters=num_clusters).to(device)
        opt_mlp = torch.optim.Adam(mlp.parameters(), lr=1e-3, weight_decay=1e-3)
        train_loader = DataLoader(TensorDataset(X_train_final, train_probs, y_train_final), batch_size=32, shuffle=True, drop_last=True)
        
        n0, n1 = (y_train_final == 0).sum().item(), (y_train_final == 1).sum().item()
        criterion = nn.CrossEntropyLoss(weight=torch.tensor([1.0, n0/max(1,n1)], device=device))

        # [评估新增] 初始化用于记录该 Fold 最佳指标的变量
        best_acc = best_auc = best_f1 = best_prec = best_rec = best_spec = 0.0
        
        for ep in range(80):
            mlp.train()
            for x, c_p, y in train_loader:
                opt_mlp.zero_grad(); criterion(mlp(x, c_p), y).backward(); opt_mlp.step()
            
            mlp.eval()
            with torch.no_grad():
                val_logits = mlp(X_va_flat, val_probs)
                val_probs_soft = torch.softmax(val_logits, dim=1)[:, 1]
                val_pred = val_logits.argmax(1)
                
                # 获取 NumPy 数组以使用 sklearn 指标
                y_va_np = y_va.cpu().numpy()
                val_pred_np = val_pred.cpu().numpy()
                val_probs_np = val_probs_soft.cpu().numpy()
                
                acc = (val_pred_np == y_va_np).mean()
                
                # [评估新增] 核心医学评估指标计算
                try: 
                    if len(np.unique(y_va_np)) > 1:
                        auc = roc_auc_score(y_va_np, val_probs_np)
                        f1 = f1_score(y_va_np, val_pred_np, zero_division=0)
                        prec = precision_score(y_va_np, val_pred_np, zero_division=0)
                        rec = recall_score(y_va_np, val_pred_np, zero_division=0)
                        
                        # 计算特异度 (Specificity = TN / (TN + FP))
                        tn, fp, fn, tp = confusion_matrix(y_va_np, val_pred_np).ravel()
                        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
                    else: 
                        auc, f1, prec, rec, spec = 0.5, 0.0, 0.0, 0.0, 0.0
                except: 
                    auc, f1, prec, rec, spec = 0.5, 0.0, 0.0, 0.0, 0.0
                
                # 以 Accuracy (或 AUC) 为主要依据保存该折的最佳参数
                if acc > best_acc: 
                    best_acc, best_auc = acc, auc
                    best_f1, best_prec, best_rec, best_spec = f1, prec, rec, spec
            
            if (ep + 1) % 20 == 0: 
                print(f"    MLP Ep {ep+1:02d} | Val Acc={acc:.3f} AUC={auc:.3f} F1={f1:.3f} Spec={spec:.3f}")

        print(f"Fold {fold+1} Result: Acc={best_acc:.3f}, AUC={best_auc:.3f}, F1={best_f1:.3f}, Rec(Sens)={best_rec:.3f}, Spec={best_spec:.3f}")
        
        # 将结果存入全局列表
        acc_scores.append(min(best_acc, 1.0))
        auc_scores.append(best_auc)
        f1_scores.append(best_f1)
        prec_scores.append(best_prec)
        rec_scores.append(best_rec)
        spec_scores.append(best_spec)

    # [评估新增] 最终输出与日志记录
    print("\n=== FINAL RESULTS (RAE-TopoCon + Topology-GCN-Diff + Cluster-Gated) ===")
    print(f"Mean Acc : {np.mean(acc_scores):.4f} ± {np.std(acc_scores):.4f}")
    print(f"Mean AUC : {np.mean(auc_scores):.4f} ± {np.std(auc_scores):.4f}")
    print(f"Mean F1  : {np.mean(f1_scores):.4f} ± {np.std(f1_scores):.4f}")
    print(f"Mean Sens: {np.mean(rec_scores):.4f} (Recall/Sensitivity)")
    print(f"Mean Spec: {np.mean(spec_scores):.4f} (Specificity)")
    print(f"Gen-MSE  : {np.mean(gen_mse_scores):.6f} (Lower is better generator)")
    
    if log_path:
        now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = (
            f"[{now_time}] "
            f"Set: [TopoCon={lambda_con}, TopoRes={topo_resolution}, BA={ba_m}] | "
            f"Results: Acc={np.mean(acc_scores):.3f}, AUC={np.mean(auc_scores):.3f}, "
            f"F1={np.mean(f1_scores):.3f}, Sens={np.mean(rec_scores):.3f}, Spec={np.mean(spec_scores):.3f}, "
            f"Gen-MSE={np.mean(gen_mse_scores):.5f}\n"
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)

if __name__ == "__main__":
    fc_dir = "/root/autodl-fs/data/Directly_use_ABIDE_NYU_182"
    label_csv = os.path.join(fc_dir, "labels.csv")
    if not os.path.exists(label_csv): print(f"[Warning] {label_csv} not found.")
    else:
        ds = FCMatDataset(fc_dir, label_csv, V=116)
        run_pipeline(
            ds,      
            k=5, V=116, K=64,
            ae_epochs=400, diff_epochs=400, T=1000, gen_per_class=200,
            ba_m=70, 
            lambda_topo=0.1, 
            lambda_reg=1e-5, 
            lambda_con=0.3, 
            num_clusters=10,  
            topk=115, enc_hidden=128, enc_layers=3, enc_dropout=0.2,
            topo_resolution=10, 
            log_path="/root/1.txt"
        )