# ═══════════════════════════════════════════════════════════════
#  Optimisation des Tournées de Livraison  —  TSP / VRP / IRP
#  Interface CustomTkinter  |  jusqu'à 100 clients
# ═══════════════════════════════════════════════════════════════

import customtkinter as ctk
import math
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ───────────────────────────────────────────────────────────────
#  PALETTE & CONSTANTES
# ───────────────────────────────────────────────────────────────
BG        = "#0d1117"
CARD      = "#161b22"
CARD2     = "#1c2128"
BORDER    = "#30363d"
ACCENT    = "#58a6ff"
ACCENT2   = "#388bfd"
SUCCESS   = "#3fb950"
WARNING   = "#d29922"
DANGER    = "#f85149"
TEXT      = "#e6edf3"
SUBTEXT   = "#8b949e"
ENTRY_BG  = "#21262d"
BTN_ADD   = "#238636"
BTN_ADD_H = "#2ea043"
BTN_RUN   = "#1f6feb"
BTN_RUN_H = "#388bfd"
BTN_DEL   = "#3d1f1f"
BTN_DEL_H = "#6b2121"

GRAPH_BG  = "#0d1117"
GRAPH_AX  = "#161b22"
COLORS_GRAPH = ["#58a6ff","#f78166","#3fb950","#e3b341","#bc8cff",
                "#39d353","#ff7b72","#79c0ff","#56d364","#ffa657"]

MAX_CLIENTS = 100

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ───────────────────────────────────────────────────────────────
#  ALGORITHMES
# ───────────────────────────────────────────────────────────────

def distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def distance_tournee(t, pts):
    return sum(distance(pts[t[i]], pts[t[i+1]]) for i in range(len(t)-1))

def two_opt(tournee, points):
    best = tournee[:]
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best)-2):
            for j in range(i+1, len(best)-1):
                new = best[:i] + best[i:j+1][::-1] + best[j+1:]
                if distance_tournee(new, points) < distance_tournee(best, points):
                    best = new; improved = True
    return best

def nearest_neighbor(depot_idx, clients_idx, points):
    nv = clients_idx[:]
    t = [depot_idx]; cur = depot_idx
    while nv:
        p = min(nv, key=lambda c: distance(points[cur], points[c]))
        t.append(p); nv.remove(p); cur = p
    t.append(depot_idx)
    return t

# --- TSP ---
def resoudre_tsp(depot, clients):
    pts  = [depot[1:]] + [c[1:] for c in clients]
    noms = [depot[0]]  + [c[0]  for c in clients]
    idx_c = list(range(1, len(pts)))
    t_init = nearest_neighbor(0, idx_c, pts)
    d_init = distance_tournee(t_init, pts)
    t_opt  = two_opt(t_init, pts)
    d_opt  = distance_tournee(t_opt, pts)
    gain   = (d_init-d_opt)/d_init*100 if d_init > 0 else 0
    return [noms[i] for i in t_opt], d_init, d_opt, gain, pts, noms, t_opt

# --- VRP ---
def resoudre_vrp(depot, clients, capacite):
    pts     = [depot[1:3]] + [c[1:3] for c in clients]
    demandes = [0] + [c[3] for c in clients]
    n = len(clients)

    routes  = [[0, i+1, 0] for i in range(n)]
    charges = [demandes[i+1] for i in range(n)]

    economies = []
    for i in range(1, n+1):
        for j in range(i+1, n+1):
            s = distance(pts[0],pts[i]) + distance(pts[0],pts[j]) - distance(pts[i],pts[j])
            economies.append((s, i, j))
    economies.sort(reverse=True)

    def find_route(idx):
        for k, r in enumerate(routes):
            if idx in r: return k
        return -1

    for (s, i, j) in economies:
        ri = find_route(i); rj = find_route(j)
        if ri == -1 or rj == -1 or ri == rj: continue
        if charges[ri] + charges[rj] > capacite: continue
        r_i = routes[ri][:]; r_j = routes[rj][:]
        if r_i[-2] != i: r_i = r_i[::-1]
        if r_j[1]  != j: r_j = r_j[::-1]
        if r_i[-2] != i or r_j[1] != j: continue
        routes[ri] = r_i[:-1] + r_j[1:]
        charges[ri] += charges[rj]
        routes.pop(rj); charges.pop(rj)

    noms = [depot[0]] + [c[0] for c in clients]
    result = []
    total  = 0
    for r in routes:
        ro   = two_opt(r, pts)
        dist = distance_tournee(ro, pts)
        ch   = sum(demandes[i] for i in ro if i != 0)
        result.append({"tournee": [noms[i] for i in ro], "charge": ch,
                        "distance": dist, "indices": ro})
        total += dist
    return result, total, pts, noms

# --- IRP amélioré ---
def resoudre_irp(depot, clients, cap_veh, periodes, seuil,
                 horizon=2, co_preventif=True, multi_tournees=True):
    """
    horizon       : nb de periodes anticipees (horizon glissant)
    co_preventif  : livrer aussi les clients proches bientot critiques
    multi_tournees: autoriser plusieurs voyages par periode si besoin
    """
    pts       = [depot[1:3]] + [c[1:3] for c in clients]
    noms      = [depot[0]]   + [c[0]   for c in clients]
    stocks    = [c[3] for c in clients]
    cap_stock = [c[4] for c in clients]
    conso     = [c[5] for c in clients]
    n         = len(clients)
    resultats = []

    for p in range(1, periodes+1):

        # ── 1. Clients obligatoires (seuil atteint aujourd'hui)
        obligatoires = set(
            i for i in range(n)
            if (stocks[i] / conso[i] if conso[i] > 0 else 999) <= seuil
        )

        # ── 2. Horizon glissant : simuler les prochains jours
        candidats_horizon = set()
        if horizon > 0:
            stocks_sim = stocks[:]
            for h in range(1, horizon + 1):
                for i in range(n):
                    stocks_sim[i] = max(0, stocks_sim[i] - conso[i])
                for i in range(n):
                    if i not in obligatoires:
                        jr = stocks_sim[i] / conso[i] if conso[i] > 0 else 999
                        if jr <= seuil:
                            candidats_horizon.add(i)

        # ── 3. Co-livraison préventive
        a_livrer = set(obligatoires)
        if co_preventif and candidats_horizon:
            if obligatoires:
                cx = sum(pts[i+1][0] for i in obligatoires) / len(obligatoires)
                cy = sum(pts[i+1][1] for i in obligatoires) / len(obligatoires)
            else:
                cx, cy = pts[0]
            candidats_tries = sorted(candidats_horizon,
                                     key=lambda i: distance(pts[i+1], (cx, cy)))
            for i in candidats_tries:
                a_livrer.add(i)

        # ── 4. Quantités à livrer (triées par urgence)
        a_livrer_tries = sorted(
            a_livrer,
            key=lambda i: (stocks[i] / conso[i] if conso[i] > 0 else 999)
        )
        livraisons = {}
        for i in a_livrer_tries:
            qte = min(cap_stock[i] - stocks[i], cap_veh)
            if qte > 0:
                livraisons[i] = qte

        # ── 5. Construction des tournées
        if not livraisons:
            tournees_detail = [{"tournee": [noms[0], noms[0]], "distance": 0, "charge": 0}]
        elif not multi_tournees:
            # Un seul passage, on remplit jusqu'à saturation
            cap_r = cap_veh
            livraisons_1 = {}
            for i in a_livrer_tries:
                qte = min(livraisons.get(i, 0), cap_r)
                if qte > 0:
                    livraisons_1[i] = qte
                    cap_r -= qte
            livraisons = livraisons_1
            if livraisons:
                idx_c = [i+1 for i in livraisons]
                t = two_opt(nearest_neighbor(0, idx_c, pts), pts)
                tournees_detail = [{
                    "tournee": [noms[i] for i in t],
                    "distance": distance_tournee(t, pts),
                    "charge": cap_veh - cap_r
                }]
            else:
                tournees_detail = [{"tournee": [noms[0], noms[0]], "distance": 0, "charge": 0}]
        else:
            # Multi-tournées : autant de voyages que nécessaire
            restants = list(a_livrer_tries)
            tournees_detail = []
            iterations = 0
            while restants and iterations < n + 1:
                iterations += 1
                cap_r = cap_veh
                voyage = []
                for i in restants:
                    qte = livraisons.get(i, 0)
                    if qte > 0 and qte <= cap_r:
                        voyage.append(i)
                        cap_r -= qte
                if not voyage:
                    break
                for i in voyage:
                    restants.remove(i)
                idx_c = [i+1 for i in voyage]
                t = two_opt(nearest_neighbor(0, idx_c, pts), pts)
                tournees_detail.append({
                    "tournee": [noms[i] for i in t],
                    "distance": distance_tournee(t, pts),
                    "charge": cap_veh - cap_r
                })
            if not tournees_detail:
                tournees_detail = [{"tournee": [noms[0], noms[0]], "distance": 0, "charge": 0}]

        dist_total    = sum(v["distance"] for v in tournees_detail)
        charge_totale = sum(v["charge"]   for v in tournees_detail)
        t_noms        = tournees_detail[0]["tournee"]

        # ── 6. Mise à jour des stocks
        ruptures = []
        for i in range(n):
            if i in livraisons:
                stocks[i] += livraisons[i]
            stocks[i] -= conso[i]
            if stocks[i] < 0:
                ruptures.append(noms[i+1])
                stocks[i] = 0

        resultats.append({
            "periode"        : p,
            "livraisons"     : {noms[i+1]: livraisons[i] for i in livraisons},
            "tournee"        : t_noms,
            "tournees_detail": tournees_detail,
            "distance"       : dist_total,
            "charge"         : charge_totale,
            "ruptures"       : ruptures,
            "stocks"         : stocks[:],
            "co_preventifs"  : [noms[i+1] for i in (a_livrer - obligatoires)]
        })

    return resultats, pts, noms


# ───────────────────────────────────────────────────────────────
#  WIDGET LIGNE CLIENT (réutilisable)
# ───────────────────────────────────────────────────────────────

class ClientRow(ctk.CTkFrame):
    """Une ligne client avec champs dynamiques + bouton supprimer."""

    def __init__(self, parent, index, fields, on_delete, **kwargs):
        """
        fields : liste de (label, default, width)
        """
        super().__init__(parent, fg_color=CARD2, corner_radius=8, **kwargs)
        self.pack(fill="x", padx=6, pady=3)

        # Numéro (stocké pour le renumérotage)
        self.num_label = ctk.CTkLabel(self, text=f"{index:02d}", width=28,
                                       font=ctk.CTkFont(size=11, weight="bold"),
                                       text_color=SUBTEXT)
        self.num_label.pack(side="left", padx=(8,4))

        self.entries = []
        for (lbl, default, w) in fields:
            sub = ctk.CTkFrame(self, fg_color="transparent")
            sub.pack(side="left", padx=4)
            ctk.CTkLabel(sub, text=lbl, font=ctk.CTkFont(size=10),
                         text_color=SUBTEXT).pack(anchor="w")
            e = ctk.CTkEntry(sub, width=w, height=28,
                             fg_color=ENTRY_BG, border_color=BORDER,
                             text_color=TEXT, font=ctk.CTkFont(size=11))
            e.insert(0, default)
            e.pack()
            self.entries.append(e)

        # Bouton supprimer
        ctk.CTkButton(self, text="✕", width=28, height=28,
                      fg_color=BTN_DEL, hover_color=BTN_DEL_H,
                      text_color=DANGER, font=ctk.CTkFont(size=12),
                      corner_radius=6,
                      command=lambda: on_delete(self)).pack(side="right", padx=8)

    def get_values(self):
        return [e.get().strip() for e in self.entries]


# ───────────────────────────────────────────────────────────────
#  SECTION CLIENTS SCROLLABLE (réutilisable)
# ───────────────────────────────────────────────────────────────

class ClientSection(ctk.CTkFrame):
    """Conteneur scrollable pour les lignes clients + bouton Ajouter."""

    def __init__(self, parent, fields_def, height=320, **kwargs):
        """
        fields_def : liste de (label, default, width) par champ
        """
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.fields_def = fields_def
        self.rows: list[ClientRow] = []
        self._MAX = MAX_CLIENTS

        # En-tête
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0,4))
        self.count_lbl = ctk.CTkLabel(header, text="0 client(s)",
                                       font=ctk.CTkFont(size=12, weight="bold"),
                                       text_color=ACCENT)
        self.count_lbl.pack(side="left")
        self.add_btn = ctk.CTkButton(header, text="＋  Ajouter un client",
                                      width=170, height=30,
                                      fg_color=BTN_ADD, hover_color=BTN_ADD_H,
                                      font=ctk.CTkFont(size=12, weight="bold"),
                                      corner_radius=8,
                                      command=self.ajouter)
        self.add_btn.pack(side="right")

        # Zone scrollable
        self.scroll = ctk.CTkScrollableFrame(self, height=height,
                                              fg_color=CARD, corner_radius=10,
                                              border_width=1, border_color=BORDER)
        self.scroll.pack(fill="x")

        # Message vide
        self.empty_lbl = ctk.CTkLabel(self.scroll,
                                       text="Aucun client — cliquez sur « Ajouter un client »",
                                       text_color=SUBTEXT, font=ctk.CTkFont(size=11))
        self.empty_lbl.pack(pady=20)

    def ajouter(self, defaults=None):
        if len(self.rows) >= self._MAX:
            return
        self.empty_lbl.pack_forget()
        idx = len(self.rows) + 1

        if defaults:
            fields = [(lbl, d, w) for (lbl, _, w), d in zip(self.fields_def, defaults)]
        else:
            fields = self.fields_def

        row = ClientRow(self.scroll, idx, fields, on_delete=self.supprimer)
        self.rows.append(row)
        self._update_counter()
        # Scroll vers le bas
        self.scroll._parent_canvas.yview_moveto(1.0)

    def supprimer(self, row: ClientRow):
        # Retirer de la liste AVANT destroy() pour éviter les problèmes de comparaison
        if row in self.rows:
            self.rows.remove(row)
        row.pack_forget()
        row.destroy()
        self._renumber()
        self._update_counter()
        if not self.rows:
            self.empty_lbl.pack(pady=20)

    def _renumber(self):
        for i, r in enumerate(self.rows):
            r.num_label.configure(text=f"{i+1:02d}")

    def _update_counter(self):
        n = len(self.rows)
        self.count_lbl.configure(text=f"{n} / {self._MAX} client(s)")
        self.add_btn.configure(state="normal" if n < self._MAX else "disabled")

    def get_clients(self):
        return [r.get_values() for r in self.rows]

    def clear(self):
        for r in self.rows[:]:
            r.pack_forget(); r.destroy()
        self.rows.clear()
        self.empty_lbl.pack(pady=20)
        self._update_counter()


# ───────────────────────────────────────────────────────────────
#  HELPERS UI
# ───────────────────────────────────────────────────────────────

def make_card(parent, title=None, padx=0, pady=(0,10)):
    outer = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12,
                          border_width=1, border_color=BORDER)
    outer.pack(fill="x", padx=padx, pady=pady)
    if title:
        ctk.CTkLabel(outer, text=title,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=ACCENT).pack(anchor="w", padx=14, pady=(10,2))
        sep = ctk.CTkFrame(outer, height=1, fg_color=BORDER)
        sep.pack(fill="x", padx=10, pady=(0,8))
    inner = ctk.CTkFrame(outer, fg_color="transparent")
    inner.pack(fill="x", padx=12, pady=(0,12))
    return inner

def labeled_entry(parent, label, default="", width=140, placeholder=""):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=3)
    ctk.CTkLabel(row, text=label, width=150, anchor="w",
                 font=ctk.CTkFont(size=12), text_color=TEXT).pack(side="left")
    e = ctk.CTkEntry(row, width=width, height=32,
                     fg_color=ENTRY_BG, border_color=BORDER,
                     placeholder_text=placeholder,
                     text_color=TEXT, font=ctk.CTkFont(size=12))
    e.insert(0, default)
    e.pack(side="left", padx=(4,0))
    return e

def run_button(parent, text, command):
    return ctk.CTkButton(parent, text=text, height=40,
                          fg_color=BTN_RUN, hover_color=BTN_RUN_H,
                          font=ctk.CTkFont(size=14, weight="bold"),
                          corner_radius=10, command=command)

def result_textbox(parent, height=180):
    tb = ctk.CTkTextbox(parent, height=height, wrap="word",
                         fg_color=CARD, border_color=BORDER, border_width=1,
                         text_color=TEXT, font=ctk.CTkFont(family="Courier", size=11),
                         corner_radius=10)
    tb.configure(state="disabled")
    return tb

def set_text(tb, text):
    tb.configure(state="normal")
    tb.delete("1.0", "end")
    tb.insert("end", text)
    tb.configure(state="disabled")

def embed_canvas(frame, fig):
    for w in frame.winfo_children():
        w.destroy()
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)


# ───────────────────────────────────────────────────────────────
#  APPLICATION PRINCIPALE
# ───────────────────────────────────────────────────────────────

class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.configure(fg_color=BG)
        self.title("Optimisation des Tournées de Livraison")
        self.geometry("1280x840")
        self.minsize(1100, 700)

        self._build_header()
        self._build_tabs()

    # ── HEADER ──────────────────────────────────────────────────
    def _build_header(self):
        h = ctk.CTkFrame(self, fg_color=CARD, height=64,
                          corner_radius=0, border_width=0)
        h.pack(fill="x")
        h.pack_propagate(False)

        ctk.CTkLabel(h, text="🚚",
                     font=ctk.CTkFont(size=26)).pack(side="left", padx=(20,8), pady=10)
        ctk.CTkLabel(h, text="Optimisation des Tournées de Livraison",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT).pack(side="left")
        ctk.CTkLabel(h, text="TSP  ·  VRP  ·  IRP",
                     font=ctk.CTkFont(size=13),
                     text_color=SUBTEXT).pack(side="right", padx=24)

    # ── ONGLETS ─────────────────────────────────────────────────
    def _build_tabs(self):
        tab_view = ctk.CTkTabview(self, fg_color=BG,
                                   segmented_button_fg_color=CARD,
                                   segmented_button_selected_color=ACCENT2,
                                   segmented_button_selected_hover_color=BTN_RUN_H,
                                   segmented_button_unselected_color=CARD,
                                   segmented_button_unselected_hover_color=CARD2,
                                   text_color=TEXT)
        tab_view.pack(fill="both", expand=True, padx=12, pady=(8,12))

        for name in ("TSP", "VRP", "IRP"):
            tab_view.add(name)

        self._build_tsp(tab_view.tab("TSP"))
        self._build_vrp(tab_view.tab("VRP"))
        self._build_irp(tab_view.tab("IRP"))

    # ── LAYOUT 2 COLONNES ───────────────────────────────────────
    def _two_col(self, tab):
        tab.columnconfigure(0, weight=0, minsize=440)
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(tab, width=430, fg_color=BG,
                                       scrollbar_button_color=BORDER,
                                       scrollbar_button_hover_color=ACCENT)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,6))

        right = ctk.CTkFrame(tab, fg_color=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        return left, right

    # ════════════════════════════════════════════════════════════
    #  TSP
    # ════════════════════════════════════════════════════════════
    def _build_tsp(self, tab):
        left, right = self._two_col(tab)

        # Dépôt
        d = make_card(left, "📍  Dépôt")
        self.tsp_dep_nom = labeled_entry(d, "Nom", "Dépôt")
        self.tsp_dep_x   = labeled_entry(d, "Coordonnée X", "0")
        self.tsp_dep_y   = labeled_entry(d, "Coordonnée Y", "0")

        # Clients
        c = make_card(left, "👥  Clients")
        fields = [("Nom","C?",70), ("X","0",58), ("Y","0",58)]
        self.tsp_clients = ClientSection(c, fields, height=340)
        self.tsp_clients.pack(fill="x")
        # Pré-remplir 4 exemples
        exemples = [("C1","2","5"),("C2","5","8"),("C3","8","3"),("C4","1","9")]
        for ex in exemples:
            self.tsp_clients.ajouter(defaults=ex)

        # Bouton résoudre
        run_button(left, "▶   Résoudre le TSP",
                   self._run_tsp).pack(fill="x", padx=4, pady=(8,4))

        # Résultats
        ctk.CTkLabel(right, text="Résultats",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=ACCENT).grid(row=0, column=0, sticky="w", padx=8, pady=(4,2))
        self.tsp_tb = result_textbox(
            ctk.CTkFrame(right, fg_color=BG).__class__(right, fg_color=BG) if False else right,
            height=155)
        self.tsp_tb.grid(row=0, column=0, sticky="ew", padx=8, pady=(28,4))

        self.tsp_graph = ctk.CTkFrame(right, fg_color=CARD,
                                       corner_radius=12, border_width=1,
                                       border_color=BORDER)
        self.tsp_graph.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,8))

    def _run_tsp(self):
        try:
            depot = (self.tsp_dep_nom.get(),
                     float(self.tsp_dep_x.get()), float(self.tsp_dep_y.get()))
            raw = self.tsp_clients.get_clients()
            if not raw: raise ValueError("Ajoutez au moins un client.")
            clients = [(r[0], float(r[1]), float(r[2])) for r in raw]
        except Exception as e:
            set_text(self.tsp_tb, f"⚠  Erreur de saisie : {e}"); return

        t_noms, d_init, d_opt, gain, pts, noms, idx_opt = resoudre_tsp(depot, clients)

        txt = (f"Tournée optimisée :\n  {' → '.join(t_noms)}\n\n"
               f"Distance initiale  : {d_init:.2f}\n"
               f"Distance optimisée : {d_opt:.2f}\n"
               f"Gain (2-opt)       : {gain:.2f} %")
        set_text(self.tsp_tb, txt)

        fig, ax = plt.subplots(figsize=(6, 4.5))
        self._style_ax(fig, ax)
        p_opt = [pts[i] for i in idx_opt]
        xs = [p[0] for p in p_opt]; ys = [p[1] for p in p_opt]
        ax.plot(xs, ys, "-", color=COLORS_GRAPH[0], linewidth=2, zorder=2)
        ax.plot(xs[0], ys[0], "s", color="white", markersize=10, zorder=4, label="Dépôt")
        ax.plot(xs[1:-1], ys[1:-1], "o", color=COLORS_GRAPH[0], markersize=8, zorder=3)
        for i, idx in enumerate(idx_opt):
            ax.annotate(noms[idx], pts[idx], color=TEXT, fontsize=8,
                        fontweight="bold", textcoords="offset points", xytext=(5,5))
        ax.set_title(f"TSP  --  distance optimisee : {d_opt:.2f}", color=TEXT, fontsize=12)
        ax.legend(facecolor=CARD, labelcolor=TEXT, fontsize=9, framealpha=0.8)
        embed_canvas(self.tsp_graph, fig)
        plt.close(fig)

    # ════════════════════════════════════════════════════════════
    #  VRP
    # ════════════════════════════════════════════════════════════
    def _build_vrp(self, tab):
        left, right = self._two_col(tab)

        d = make_card(left, "📍  Dépôt")
        self.vrp_dep_nom = labeled_entry(d, "Nom", "Dépôt")
        self.vrp_dep_x   = labeled_entry(d, "Coordonnée X", "0")
        self.vrp_dep_y   = labeled_entry(d, "Coordonnée Y", "0")

        v = make_card(left, "🚛  Véhicules")
        self.vrp_nb_veh  = labeled_entry(v, "Nombre de véhicules", "2")
        self.vrp_cap_veh = labeled_entry(v, "Capacité maximale",   "15")

        c = make_card(left, "👥  Clients")
        fields = [("Nom","C?",60), ("X","0",48), ("Y","0",48), ("Demande","1",55)]
        self.vrp_clients = ClientSection(c, fields, height=300)
        self.vrp_clients.pack(fill="x")
        exemples = [("A","2","5","4"),("B","5","8","3"),("C","8","3","5"),
                    ("D","1","9","2"),("E","6","1","6")]
        for ex in exemples:
            self.vrp_clients.ajouter(defaults=ex)

        run_button(left, "▶   Résoudre le VRP",
                   self._run_vrp).pack(fill="x", padx=4, pady=(8,4))

        ctk.CTkLabel(right, text="Résultats",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=ACCENT).grid(row=0, column=0, sticky="w", padx=8, pady=(4,2))
        self.vrp_tb = result_textbox(right, height=155)
        self.vrp_tb.grid(row=0, column=0, sticky="ew", padx=8, pady=(28,4))

        self.vrp_graph = ctk.CTkFrame(right, fg_color=CARD,
                                       corner_radius=12, border_width=1,
                                       border_color=BORDER)
        self.vrp_graph.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,8))

    def _run_vrp(self):
        try:
            depot = (self.vrp_dep_nom.get(),
                     float(self.vrp_dep_x.get()), float(self.vrp_dep_y.get()))
            cap   = float(self.vrp_cap_veh.get())
            nb_v  = int(self.vrp_nb_veh.get())
            raw   = self.vrp_clients.get_clients()
            if not raw: raise ValueError("Ajoutez au moins un client.")
            clients = [(r[0], float(r[1]), float(r[2]), float(r[3])) for r in raw]
        except Exception as e:
            set_text(self.vrp_tb, f"⚠  Erreur de saisie : {e}"); return

        result, total, pts, noms = resoudre_vrp(depot, clients, cap)

        lines = []
        for k, r in enumerate(result):
            lines.append(f"Véhicule {k+1} : {' → '.join(r['tournee'])}")
            lines.append(f"  Charge : {r['charge']:.0f} / {cap:.0f}   Distance : {r['distance']:.2f}")
        lines.append(f"\nDistance totale : {total:.2f}")
        set_text(self.vrp_tb, "\n".join(lines))

        fig, ax = plt.subplots(figsize=(6, 4.5))
        self._style_ax(fig, ax)
        ax.plot(pts[0][0], pts[0][1], "s", color="white", markersize=11,
                zorder=5, label=noms[0])
        ax.annotate(noms[0], pts[0], color=TEXT, fontsize=8, fontweight="bold",
                    textcoords="offset points", xytext=(5,5))
        handles = [mpatches.Patch(color="white", label=noms[0])]
        for k, r in enumerate(result):
            col = COLORS_GRAPH[k % len(COLORS_GRAPH)]
            p = [pts[i] for i in r["indices"]]
            ax.plot([x[0] for x in p], [x[1] for x in p], "o-",
                    color=col, linewidth=2, markersize=7, zorder=3)
            for idx in r["indices"]:
                if idx != 0:
                    ax.annotate(noms[idx], pts[idx], color=col, fontsize=8,
                                textcoords="offset points", xytext=(5,5))
            handles.append(mpatches.Patch(color=col, label=f"Véhicule {k+1}"))
        ax.legend(handles=handles, facecolor=CARD, labelcolor=TEXT,
                  fontsize=9, framealpha=0.8)
        ax.set_title(f"VRP -- distance totale : {total:.2f}", color=TEXT, fontsize=12)
        embed_canvas(self.vrp_graph, fig)
        plt.close(fig)

    # IRP
    def _build_irp(self, tab):
        left, right = self._two_col(tab)

        d = make_card(left, "Depot")
        self.irp_dep_nom = labeled_entry(d, "Nom", "Depot")
        self.irp_dep_x   = labeled_entry(d, "Coordonnee X", "0")
        self.irp_dep_y   = labeled_entry(d, "Coordonnee Y", "0")

        p = make_card(left, "Parametres")
        self.irp_cap_veh  = labeled_entry(p, "Capacite vehicule", "30")
        self.irp_periodes = labeled_entry(p, "Nombre de periodes", "5")
        self.irp_seuil    = labeled_entry(p, "Seuil (jours)", "2")
        self.irp_horizon  = labeled_entry(p, "Horizon glissant", "2")

        opt = make_card(left, "Ameliorations")
        self.irp_co_prev_var  = ctk.BooleanVar(value=True)
        self.irp_multi_var    = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt, text="Co-livraison preventive",
                        variable=self.irp_co_prev_var,
                        checkmark_color=BG, fg_color=ACCENT, hover_color=ACCENT2,
                        text_color=TEXT, font=ctk.CTkFont(size=12)).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(opt, text="Multi-tournees par periode",
                        variable=self.irp_multi_var,
                        checkmark_color=BG, fg_color=ACCENT, hover_color=ACCENT2,
                        text_color=TEXT, font=ctk.CTkFont(size=12)).pack(anchor="w", pady=3)

        c = make_card(left, "Clients")
        fields = [("Nom","C?",50),("X","0",42),("Y","0",42),
                  ("Stock","10",46),("Cap.","20",46),("Conso","3",46)]
        self.irp_clients = ClientSection(c, fields, height=280)
        self.irp_clients.pack(fill="x")
        exemples = [("A","3","4","10","20","3"),("B","7","2","8","25","4"),
                    ("C","5","8","15","30","5")]
        for ex in exemples:
            self.irp_clients.ajouter(defaults=ex)

        run_button(left, "Resoudre l'IRP",
                   self._run_irp).pack(fill="x", padx=4, pady=(8,4))

        # Label résultats
        ctk.CTkLabel(right, text="Resultats",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=ACCENT).grid(row=0, column=0, columnspan=2,
                                             sticky="w", padx=8, pady=(4,2))
        self.irp_tb = result_textbox(right, height=160)
        self.irp_tb.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(28,4))

        # Sélecteur de période (affiché seulement après résolution)
        right.columnconfigure(0, weight=1)
        right.columnconfigure(1, weight=1)
        right.rowconfigure(2, weight=1)

        nav = ctk.CTkFrame(right, fg_color="transparent")
        nav.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(2,2))
        ctk.CTkLabel(nav, text="Periode :", font=ctk.CTkFont(size=12),
                     text_color=SUBTEXT).pack(side="left", padx=(0,6))
        self.irp_period_var = ctk.StringVar(value="1")
        self.irp_period_cb  = ctk.CTkComboBox(nav, variable=self.irp_period_var,
                                               values=["—"], width=80, height=28,
                                               fg_color=ENTRY_BG, border_color=BORDER,
                                               button_color=ACCENT2, dropdown_fg_color=CARD2,
                                               text_color=TEXT,
                                               command=lambda v: self._draw_irp_route(int(v)))
        self.irp_period_cb.pack(side="left")

        # Graphique tournée (gauche) + stocks (droite)
        self.irp_route_graph = ctk.CTkFrame(right, fg_color=CARD,
                                             corner_radius=12, border_width=1,
                                             border_color=BORDER)
        self.irp_route_graph.grid(row=2, column=0, sticky="nsew", padx=(8,4), pady=(0,8))

        self.irp_stock_graph = ctk.CTkFrame(right, fg_color=CARD,
                                             corner_radius=12, border_width=1,
                                             border_color=BORDER)
        self.irp_stock_graph.grid(row=2, column=1, sticky="nsew", padx=(4,8), pady=(0,8))

        # Stockage des résultats pour navigation
        self._irp_resultats = []
        self._irp_pts       = []
        self._irp_noms      = []
        self._irp_clients   = []

    def _draw_irp_route(self, periode):
        """Dessine la carte de tournée pour la période sélectionnée."""
        if not self._irp_resultats:
            return
        r    = next((x for x in self._irp_resultats if x["periode"] == periode), None)
        if r is None:
            return
        pts  = self._irp_pts
        noms = self._irp_noms

        fig, ax = plt.subplots(figsize=(4.5, 3.8))
        self._style_ax(fig, ax)

        # Tous les points en gris clair (non visités)
        for i in range(1, len(pts)):
            ax.plot(pts[i][0], pts[i][1], "o", color=SUBTEXT, markersize=7, zorder=2)
            ax.annotate(noms[i], pts[i], color=SUBTEXT, fontsize=8,
                        textcoords="offset points", xytext=(4, 4))

        # Dépôt
        ax.plot(pts[0][0], pts[0][1], "s", color="white", markersize=10, zorder=5)
        ax.annotate(noms[0], pts[0], color="white", fontsize=8, fontweight="bold",
                    textcoords="offset points", xytext=(4, 4))

        # Tournée de la période
        tournee_idx = r["tournee"]   # liste de noms
        # Reconstituer les indices depuis les noms
        nom_to_idx = {n: i for i, n in enumerate(noms)}
        idx_list   = [nom_to_idx[n] for n in tournee_idx if n in nom_to_idx]
        tournees_detail = r.get("tournees_detail", [{"tournee": r["tournee"], "distance": r["distance"], "charge": r["charge"]}])
        for v_idx, voy in enumerate(tournees_detail):
            col_v = COLORS_GRAPH[v_idx % len(COLORS_GRAPH)]
            v_idx_list = [nom_to_idx[nm] for nm in voy["tournee"] if nm in nom_to_idx]
            if len(v_idx_list) > 1:
                t_pts = [pts[i] for i in v_idx_list]
                xs = [pp[0] for pp in t_pts]
                ys = [pp[1] for pp in t_pts]
                lbl_v = "Voyage " + str(v_idx+1) if len(tournees_detail) > 1 else None
                ax.plot(xs, ys, "-", color=col_v, linewidth=2, zorder=3, label=lbl_v)
                for idx in v_idx_list:
                    if idx != 0:
                        ax.plot(pts[idx][0], pts[idx][1], "o",
                                color=col_v, markersize=9, zorder=4)
                        livr = r["livraisons"].get(noms[idx], 0)
                        prev = noms[idx] in r.get("co_preventifs", [])
                        suffix = (" +"+str(round(livr)) if livr > 0 else "") + (" [P]" if prev else "")
                        ax.annotate(noms[idx]+suffix, pts[idx], color=col_v, fontsize=8,
                                    fontweight="bold",
                                    textcoords="offset points", xytext=(4, 4))
        if len(tournees_detail) > 1:
            ax.legend(facecolor=CARD, labelcolor=TEXT, fontsize=8, framealpha=0.8)

        no_livr = not bool(r["livraisons"])
        titre = (("Periode " + str(periode) + "  --  aucune livraison") if no_livr
                 else ("Periode " + str(periode) + "  --  dist : " + str(round(r["distance"],2)) + "  charge : " + str(round(r["charge"]))))
        ax.set_title(titre, color=TEXT, fontsize=10)
        embed_canvas(self.irp_route_graph, fig)
        plt.close(fig)

    def _run_irp(self):
        try:
            depot = (self.irp_dep_nom.get(),
                     float(self.irp_dep_x.get()), float(self.irp_dep_y.get()))
            cap_v   = float(self.irp_cap_veh.get())
            per     = int(self.irp_periodes.get())
            seuil   = float(self.irp_seuil.get())
            horizon = int(self.irp_horizon.get())
            co_prev = self.irp_co_prev_var.get()
            multi   = self.irp_multi_var.get()
            raw     = self.irp_clients.get_clients()
            if not raw:
                raise ValueError("Ajoutez au moins un client.")
            clients = [(r[0], float(r[1]), float(r[2]), float(r[3]),
                        float(r[4]), float(r[5])) for r in raw]
        except Exception as e:
            set_text(self.irp_tb, f"Erreur de saisie : {e}")
            return

        resultats, pts, noms = resoudre_irp(
            depot, clients, cap_v, per, seuil,
            horizon=horizon, co_preventif=co_prev, multi_tournees=multi
        )

        self._irp_resultats = resultats
        self._irp_pts       = pts
        self._irp_noms      = noms
        self._irp_clients   = clients

        periodes_vals = [str(r["periode"]) for r in resultats]
        self.irp_period_cb.configure(values=periodes_vals)
        self.irp_period_var.set(periodes_vals[0])

        lines = []; dist_tot = 0
        for r in resultats:
            lines.append("-- Periode " + str(r["periode"]) + " " + "-"*28)
            if r["livraisons"]:
                lines.append("  Livraisons : " +
                              ", ".join(k + " +" + str(round(v))
                                        for k, v in r["livraisons"].items()))
            else:
                lines.append("  Aucune livraison.")
            if r.get("co_preventifs"):
                lines.append("  Preventifs : " + ", ".join(r["co_preventifs"]))
            nb_v = len(r.get("tournees_detail", []))
            if nb_v > 1:
                lines.append("  " + str(nb_v) + " voyages :")
                for k, voy in enumerate(r["tournees_detail"]):
                    lines.append("    Voyage " + str(k+1) + " : " +
                                 " -> ".join(voy["tournee"]) +
                                 "  (dist:" + str(round(voy["distance"],2)) +
                                 " ch:" + str(round(voy["charge"])) + ")")
            else:
                lines.append("  Tournee  : " + " -> ".join(r["tournee"]))
            lines.append("  Charge   : " + str(round(r["charge"])) +
                         "  |  Dist. : " + str(round(r["distance"], 2)))
            if r["ruptures"]:
                lines.append("  RUPTURES : " + ", ".join(r["ruptures"]))
            dist_tot += r["distance"]
        lines.append("\nDistance totale cumulee : " + str(round(dist_tot, 2)))
        set_text(self.irp_tb, "\n".join(lines))

        self._draw_irp_route(1)

        fig, ax = plt.subplots(figsize=(4.5, 3.8))
        self._style_ax(fig, ax)
        x_vals = [r["periode"] for r in resultats]
        for i, c in enumerate(clients):
            y_vals = [r["stocks"][i] for r in resultats]
            col = COLORS_GRAPH[i % len(COLORS_GRAPH)]
            ax.plot(x_vals, y_vals, "o-", color=col, linewidth=2,
                    markersize=6, label=c[0])
            ax.fill_between(x_vals, y_vals, alpha=0.08, color=col)
        ax.axhline(0, color=DANGER, linestyle="--", linewidth=1.2, label="Rupture")
        ax.set_xlabel("Periode", color=TEXT, fontsize=9)
        ax.set_ylabel("Stock", color=TEXT, fontsize=9)
        ax.set_title("Evolution des stocks", color=TEXT, fontsize=11)
        ax.legend(facecolor=CARD, labelcolor=TEXT, fontsize=8, framealpha=0.8)
        ax.set_xticks(x_vals)
        embed_canvas(self.irp_stock_graph, fig)
        plt.close(fig)

    def _style_ax(self, fig, ax):
        fig.patch.set_facecolor(GRAPH_BG)
        ax.set_facecolor(GRAPH_AX)
        ax.tick_params(colors=SUBTEXT, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.grid(True, color=BORDER, linewidth=0.5, alpha=0.6)
        fig.tight_layout(pad=1.5)


if __name__ == "__main__":
    app = App()
    app.mainloop()
