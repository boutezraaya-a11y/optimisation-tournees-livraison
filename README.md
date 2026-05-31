# 🚚 Optimisation des Tournées de Livraison
### TSP · VRP · IRP — ENSA Tanger | Mai 2026

Application desktop développée en Python 3 avec interface graphique CustomTkinter (thème sombre) et visualisations Matplotlib.

---

## 👥 Réalisé par
Aya Boutezra · Safae Chendoudi · Nada Bourhes · Wijdane Ghailan · Nada Zairi 
**Module :** Optimisation combinatoire — Tournées de livraison  
**Établissement :** ENSA Tanger

---

## 📋 Fonctionnalités

| Méthode | Description |
|---------|-------------|
| **TSP** | Travelling Salesman Problem — 1 véhicule, tous les clients |
| **VRP** | Vehicle Routing Problem — plusieurs véhicules avec capacité |
| **IRP** | Inventory Routing Problem — gestion des stocks multi-périodes |

### Algorithmes implémentés
- **Plus Proche Voisin** — construction de la tournée initiale
- **2-opt** — optimisation locale (suppression des croisements)
- **Clarke & Wright Savings** — construction des routes VRP
- **Politique de seuil + Horizon glissant** — planification IRP
- **Co-livraison préventive** — mutualisation des déplacements
- **Multi-tournées** — plusieurs voyages par période si nécessaire

---

## ⚙️ Installation

### 1. Cloner le dépôt
```bash
git clone https://github.com/boutezraaya-a11y/optimisation-tournees-livraison.git
cd optimisation-tournees-livraison
```

### 2. Installer les dépendances
```bash
pip install customtkinter matplotlib
```

### 3. Lancer l'application
```bash
python APPLICATION_Optimisation_livraison__2_.py
```

---

## 🖥️ Captures d'écran

> *(Ajouter captures d'écran ici)*

---

## 📁 Structure du projet

```
optimisation-tournees-livraison/
│
├── APPLICATION_Optimisation_livraison__2_.py   # Application principale
└── README.md
```

---

## 📚 Références
- Clarke, G. & Wright, J.W. (1964). *Scheduling of Vehicles from a Central Depot to a Number of Delivery Points*
- Or, I. (1976). *Travelling Salesman-Type Combinatorial Problems*
