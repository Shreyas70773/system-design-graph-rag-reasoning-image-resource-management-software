# Brand-Aligned Content Generation Platform - Frontend

## Quick Start

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Configure environment

The `.env` file is already set up to connect to the local backend:

```
VITE_API_URL=http://localhost:8000
```

### 3. Run the development server

```bash
npm run dev
```

The app will be available at **http://localhost:5173**

## Pages

| Route | Description |
|-------|-------------|
| `/` | Home - Enter website URL |
| `/onboarding` | Multi-step brand setup |
| `/dashboard/:brandId` | Brand dashboard |
| `/generate/:brandId` | Content generation form |
| `/results/:brandId` | View generated content |
| `/history/:brandId` | Generation history |

## Project Structure

```
frontend/
├── src/
│   ├── main.jsx           # App entry point
│   ├── App.jsx            # Routes definition
│   ├── index.css          # Tailwind + custom styles
│   ├── components/
│   │   └── Layout.jsx     # Main layout with header/footer
│   ├── pages/
│   │   ├── Home.jsx       # Landing page with URL input
│   │   ├── Onboarding.jsx # Brand setup wizard
│   │   ├── Dashboard.jsx  # Brand overview
│   │   ├── Generate.jsx   # Content generation form
│   │   ├── Results.jsx    # Show generated content
│   │   └── History.jsx    # Past generations
│   └── services/
│       └── api.js         # API client functions
├── tailwind.config.js
├── postcss.config.js
├── .env
└── package.json
```

## Key Dependencies

- **React 18** - UI framework
- **React Router DOM** - Client-side routing
- **Axios** - HTTP client
- **Tailwind CSS** - Utility-first CSS
- **Lucide React** - Icons

## Deployment to Vercel

1. Push code to GitHub
2. Import project in Vercel
3. Set environment variable: `VITE_API_URL=https://your-backend.railway.app`
4. Deploy!
