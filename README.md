# Conciliador - Assessoria Egara

Sistema intel·ligent de conciliació de comptes amb **Waterfall Reconciliation** (Referència → Import Exacte → FIFO).

## Característiques

- 🎯 **Conciliació en 3 Fases:** Prioritza coincidències explícites sobre FIFO
- 🎨 **Disseny Apple:** Interfície moderna amb glassmorphism
- 📊 **Badges Visuals:** Indica com es va fer cada match (🔗 Ref, 💯 Exact, ⏰ FIFO)
- ⚡ **Temps Real:** Slider de tolerància interactiu
- 🌍 **Multi-idioma:** Interfície en espanyol

## Tech Stack

- **Backend:** FastAPI (Python 3.10+)
- **Frontend:** React + Vite
- **Processament:** Pandas, NumPy, OpenPyXL

## Com executar localment

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Deploy a Render.com

1. Connecta aquest repositori a Render
2. Crea un **Web Service** (Backend) amb:
   - Root: `backend`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Crea un **Static Site** (Frontend) amb:
   - Root: `frontend`
   - Build: `npm install && npm run build`
   - Publish: `dist`

## Configuració

Ajusta els prefixos de comptes al panell de configuració:
- **Clientes (AR):** Per defecte `43`
- **Proveedores (AP):** Per defecte `40`
