# JARVIS Frontend — React 18 + Vite + Tailwind CSS

The frontend is a modern single-page application built with React 18, Vite, Tailwind CSS with glassmorphism design system, and Zustand for global state management. It provides real-time dashboards, lead management, campaign monitoring, and operational intelligence visualization.

---

## Overview

| Aspect | Details |
|---|---|
| **Framework** | React 18 (functional components) |
| **Build Tool** | Vite 5+ (ESM, fast HMR) |
| **Styling** | Tailwind CSS 3 + Glassmorphism |
| **State** | Zustand (lightweight, reactive) |
| **HTTP** | Axios (with interceptors) |
| **Views** | 18+ dashboard components |
| **Design** | Responsive, mobile-first |

---

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard/               # Main dashboard view
│   │   ├── Leads/                   # Lead discovery & management
│   │   │   ├── LeadDiscovery.jsx
│   │   │   ├── LeadScoring.jsx
│   │   │   ├── LeadList.jsx
│   │   │   └── LeadDetail.jsx
│   │   │
│   │   ├── Outreach/                # Email campaigns
│   │   │   ├── CampaignBuilder.jsx
│   │   │   ├── SequenceEditor.jsx
│   │   │   ├── SendAnalytics.jsx
│   │   │   └── ReplyMonitor.jsx
│   │   │
│   │   ├── Intelligence/            # Briefings & insights
│   │   │   ├── Briefing.jsx
│   │   │   ├── TechRadar.jsx
│   │   │   ├── MarketIntel.jsx
│   │   │   └── CompetitorAnalysis.jsx
│   │   │
│   │   ├── Proposals/               # Proposal management
│   │   │   ├── ProposalBuilder.jsx
│   │   │   ├── ProposalList.jsx
│   │   │   └── ApprovalWorkflow.jsx
│   │   │
│   │   ├── Revenue/                 # Financial dashboards
│   │   │   ├── InvoiceList.jsx
│   │   │   ├── RevenueAnalytics.jsx
│   │   │   └── PaymentTracking.jsx
│   │   │
│   │   ├── Operations/              # System operations
│   │   │   ├── SchedulerJobs.jsx
│   │   │   ├── SystemHealth.jsx
│   │   │   ├── AlertConfig.jsx
│   │   │   └── TeamRegistry.jsx
│   │   │
│   │   ├── Common/                  # Reusable components
│   │   │   ├── Sidebar.jsx          # Navigation menu
│   │   │   ├── Header.jsx           # Top bar with user menu
│   │   │   ├── Card.jsx             # Glass card component
│   │   │   ├── Button.jsx           # Styled button
│   │   │   ├── Modal.jsx            # Dialog component
│   │   │   ├── Table.jsx            # Data table
│   │   │   ├── Chart.jsx            # Chart wrapper
│   │   │   ├── Badge.jsx            # Status badge
│   │   │   ├── Spinner.jsx          # Loading indicator
│   │   │   └── Toast.jsx            # Notification toast
│   │   │
│   │   └── Auth/
│   │       ├── LoginForm.jsx
│   │       └── ProtectedRoute.jsx
│   │
│   ├── services/
│   │   ├── api.js                   # Axios API helpers (80+ methods)
│   │   ├── auth.js                  # Authentication utilities
│   │   └── websocket.js             # Real-time updates (optional)
│   │
│   ├── store/
│   │   ├── useJarvisStore.js        # Global Zustand state
│   │   ├── useAuthStore.js          # Authentication state
│   │   ├── useLeadStore.js          # Lead management state
│   │   ├── useOutreachStore.js      # Outreach state
│   │   └── useUIStore.js            # UI state (modals, toasts)
│   │
│   ├── hooks/
│   │   ├── useApi.js                # API call hook
│   │   ├── usePagination.js         # Pagination logic
│   │   ├── useDebounce.js           # Input debouncing
│   │   └── useLocalStorage.js       # Persistent state
│   │
│   ├── utils/
│   │   ├── formatters.js            # Date, currency, text formatting
│   │   ├── validators.js            # Form validation
│   │   ├── constants.js             # App-wide constants
│   │   └── helpers.js               # Utility functions
│   │
│   ├── styles/
│   │   ├── globals.css              # Global styles
│   │   ├── components.css           # Component styles
│   │   └── animations.css           # Keyframe animations
│   │
│   ├── App.jsx                      # Root component & router
│   └── main.jsx                     # Entry point
│
├── public/
│   ├── favicon.ico
│   ├── assets/                      # Images, icons, fonts
│   └── manifest.json
│
├── index.html                       # HTML template
├── vite.config.js                   # Vite configuration
├── tailwind.config.js               # Tailwind CSS config
├── postcss.config.js                # PostCSS config
├── package.json                     # Dependencies
├── .eslintrc.cjs                    # ESLint config
├── .prettierrc                      # Prettier config
└── README.md                        # This file
```

---

## Installation & Setup

### Prerequisites

```bash
node --version       # 18+
npm --version        # 9+
```

### Local Development

```bash
# 1. Install dependencies
npm install

# 2. Copy environment file
cp .env.example .env
# Edit .env with your API endpoint

# 3. Start development server
npm run dev

# 4. Open in browser
# http://localhost:5173
```

### Build for Production

```bash
# Build
npm run build

# Preview production build locally
npm run preview

# Output: dist/ folder ready for deployment
```

---

## Environment Configuration

### Development (.env)

```bash
VITE_API_URL=http://localhost:8000
VITE_API_BASE_PATH=/api/v1
VITE_WS_URL=ws://localhost:8000/ws
VITE_APP_NAME=JARVIS
VITE_DEBUG=true
```

### Production (.env.production)

```bash
VITE_API_URL=https://api.aliyarsolutions.com
VITE_API_BASE_PATH=/api/v1
VITE_WS_URL=wss://api.aliyarsolutions.com/ws
VITE_APP_NAME=JARVIS
VITE_DEBUG=false
```

---

## Component Architecture

### Design System (Glassmorphism)

The frontend uses a consistent glassmorphism design with:
- **Colors:** Dark theme with glass panel overlays
- **Opacity:** 10-20% white on colored backgrounds
- **Blur:** 10-15px backdrop filter for depth
- **Shadows:** Soft shadows for elevation
- **Spacing:** 8px base unit for consistency

### Common Components

**Card**
```jsx
<Card className="glass-panel">
  <Card.Header>
    <h3>Title</h3>
  </Card.Header>
  <Card.Body>
    Content here
  </Card.Body>
</Card>
```

**Button**
```jsx
<Button variant="primary" size="lg" onClick={handleClick}>
  Action
</Button>
```

**Modal**
```jsx
<Modal isOpen={open} onClose={handleClose} title="Dialog">
  <Modal.Body>Content</Modal.Body>
  <Modal.Footer>
    <Button onClick={handleClose}>Close</Button>
  </Modal.Footer>
</Modal>
```

**Table**
```jsx
<Table 
  columns={[
    { header: "Name", key: "name" },
    { header: "Score", key: "score", render: (v) => `${v}%` },
  ]}
  data={rows}
  onRowClick={handleRowClick}
/>
```

---

## State Management (Zustand)

### Global Store

```javascript
import { create } from 'zustand';

export const useJarvisStore = create((set) => ({
  // State
  leads: [],
  selectedLead: null,
  loading: false,
  
  // Actions
  setLeads: (leads) => set({ leads }),
  setSelectedLead: (lead) => set({ selectedLead: lead }),
  setLoading: (loading) => set({ loading }),
  
  // Async actions
  fetchLeads: async () => {
    set({ loading: true });
    try {
      const leads = await api.leads.list();
      set({ leads, loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },
}));
```

### Usage in Components

```jsx
import { useJarvisStore } from '../store/useJarvisStore';

function LeadList() {
  const { leads, loading, selectedLead, fetchLeads } = useJarvisStore();
  
  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);
  
  if (loading) return <Spinner />;
  
  return (
    <div>
      {leads.map(lead => (
        <LeadCard key={lead.id} lead={lead} />
      ))}
    </div>
  );
}
```

---

## API Integration

### Axios Client

```javascript
// services/api.js
import axios from 'axios';

const client = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL}${import.meta.env.VITE_API_BASE_PATH}`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor
client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
    }
    throw error;
  }
);

export default client;
```

### API Methods

```javascript
// services/api.js

export const leads = {
  list: () => client.get('/leads'),
  get: (id) => client.get(`/leads/${id}`),
  create: (data) => client.post('/leads', data),
  score: (id) => client.post(`/leads/${id}/score`),
  discover: (query) => client.post('/leads/discover', query),
};

export const outreach = {
  list: () => client.get('/outreach'),
  send: (leadId, templateId) => client.post('/outreach/send', { leadId, templateId }),
  getAnalytics: () => client.get('/outreach/analytics'),
};

export const intelligence = {
  getBriefing: () => client.get('/intelligence/briefing'),
  getTechRadar: () => client.get('/intelligence/tech-radar'),
  getMarketIntel: () => client.get('/intelligence/market-intel'),
};

// ... 70+ more methods
```

---

## Hooks

### useApi

```javascript
import { useApi } from '../hooks/useApi';

function MyComponent() {
  const { data, loading, error, call } = useApi();
  
  const handleFetch = async () => {
    const result = await call(() => api.leads.list());
    console.log(result);
  };
  
  return (
    <div>
      <button onClick={handleFetch} disabled={loading}>
        {loading ? 'Loading...' : 'Fetch Leads'}
      </button>
      {error && <p>{error.message}</p>}
      {data && <p>Loaded {data.length} leads</p>}
    </div>
  );
}
```

### useDebounce

```javascript
import { useDebounce } from '../hooks/useDebounce';

function SearchLeads() {
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedTerm = useDebounce(searchTerm, 300);
  
  useEffect(() => {
    if (debouncedTerm) {
      api.leads.search({ q: debouncedTerm });
    }
  }, [debouncedTerm]);
  
  return (
    <input 
      type="text"
      placeholder="Search leads..."
      value={searchTerm}
      onChange={(e) => setSearchTerm(e.target.value)}
    />
  );
}
```

---

## Styling & Tailwind CSS

### Glassmorphism Design

```jsx
// Card with glass effect
<div className="
  bg-white/10 
  backdrop-blur-xl 
  rounded-lg 
  border border-white/20 
  shadow-lg 
  p-6
">
  {content}
</div>
```

### Responsive Design

```jsx
// Mobile-first responsive
<div className="
  grid 
  grid-cols-1 
  md:grid-cols-2 
  lg:grid-cols-3 
  gap-4
">
  {items.map(item => <Card key={item.id} item={item} />)}
</div>
```

### Custom CSS

```css
/* styles/components.css */

.glass-panel {
  @apply bg-white/10 backdrop-blur-xl rounded-lg 
         border border-white/20 shadow-lg p-6;
}

.btn-primary {
  @apply bg-blue-600 text-white px-4 py-2 rounded-lg
         hover:bg-blue-700 transition-colors;
}

@keyframes fadeIn {
  from { @apply opacity-0; }
  to { @apply opacity-100; }
}

.fade-in {
  @apply animate-[fadeIn_0.3s_ease-in-out];
}
```

---

## Testing

### Unit Tests

```bash
# Install testing libraries
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom

# Run tests
npm run test

# Watch mode
npm run test:watch

# Coverage
npm run test:coverage
```

### Example Test

```javascript
// src/components/Button.test.jsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Button from './Button';

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick handler', async () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click</Button>);
    
    await userEvent.click(screen.getByText('Click'));
    expect(handleClick).toHaveBeenCalledOnce();
  });
});
```

---

## Development Workflow

### Code Quality

```bash
# Linting
npm run lint

# Format code
npm run format

# Type checking (if using TypeScript)
npm run type-check
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feat/my-feature

# Make changes
npm run dev   # Test locally

# Commit
git commit -m "feat: add my feature"

# Push
git push -u origin feat/my-feature

# Create pull request on GitHub
```

---

## Performance Optimization

### Code Splitting

```jsx
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./views/Dashboard'));

<Suspense fallback={<Spinner />}>
  <Dashboard />
</Suspense>
```

### Memoization

```jsx
import { memo } from 'react';

const LeadCard = memo(({ lead, onSelect }) => (
  <div onClick={() => onSelect(lead)}>
    {lead.name}
  </div>
));
```

### Image Optimization

```jsx
// Use modern image formats with fallback
<picture>
  <source srcSet="image.webp" type="image/webp" />
  <img src="image.png" alt="Description" />
</picture>
```

---

## Deployment

### Static Hosting (Vercel, Netlify)

```bash
# Build
npm run build

# Output: dist/ folder
# Deploy dist/ folder to hosting provider
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration

```nginx
# nginx.conf
server {
  listen 80;
  root /usr/share/nginx/html;
  index index.html;
  
  # React Router SPA configuration
  location / {
    try_files $uri $uri/ /index.html;
  }
  
  # API proxy
  location /api/ {
    proxy_pass http://backend:8000/api/;
    proxy_http_version 1.1;
  }
}
```

---

## Troubleshooting

### Vite Build Issues

```bash
# Clear node_modules and cache
rm -rf node_modules package-lock.json
npm install

# Rebuild
npm run build
```

### CORS Errors

```bash
# If backend API not accessible:
# 1. Check VITE_API_URL is correct
# 2. Ensure backend CORS headers are set
# 3. Check browser console for exact error

# Development: Backend should have CORS enabled
# See backend/app/middleware.py
```

### State Not Updating

```bash
# Use Zustand devtools for debugging
import { devtools } from 'zustand/middleware';

export const useStore = devtools(
  create((set) => ({
    // ...
  })),
  'StoreName'
);
```

### Performance Issues

```bash
# Analyze bundle size
npm run build
# Check dist/ size

# Profile component performance
import { Profiler } from 'react';

<Profiler id="MyComponent" onRender={onRender}>
  <MyComponent />
</Profiler>
```

---

## Common Tasks

### Add a New Page/View

1. Create component: `src/components/MyView/MyView.jsx`
2. Add route in `App.jsx`:
   ```jsx
   import MyView from './components/MyView/MyView';
   
   function App() {
     const views = [
       // ... existing views
       { id: 'my-view', label: 'My View', component: MyView },
     ];
   }
   ```
3. Add navigation link in `Sidebar.jsx`

### Connect to New API Endpoint

1. Add to `services/api.js`:
   ```javascript
   export const myFeature = {
     list: () => client.get('/my-feature'),
     create: (data) => client.post('/my-feature', data),
   };
   ```
2. Use in component:
   ```javascript
   const data = await api.myFeature.list();
   ```

### Add Global State

1. Create store: `src/store/useMyStore.js`
2. Define state and actions
3. Use in components: `const { state, action } = useMyStore();`

---

## Resources

- **React Documentation:** https://react.dev
- **Vite Documentation:** https://vitejs.dev
- **Tailwind CSS:** https://tailwindcss.com
- **Zustand:** https://github.com/pmndrs/zustand
- **Axios:** https://axios-http.com

---

**Last Updated:** 2024-07-02  
**Version:** 1.0.0-MVP
