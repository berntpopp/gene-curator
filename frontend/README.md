# Gene Curator Frontend

Modern Vue 3 + Vite frontend for the Gene Curator platform.

## Quick Start

### Prerequisites
- Node.js 18+ 
- npm

### Development Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

3. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000 (must be running)

### Development Credentials

- **Admin**: `admin@gene-curator.dev` / `admin123`
- **Curator**: `curator@gene-curator.dev` / `curator123`
- **Viewer**: `viewer@gene-curator.dev` / `viewer123`

## Technology Stack

- **Vue 3** - Progressive JavaScript framework
- **Vite** - Fast build tool and development server
- **Vuetify 3** - Material Design component library
- **Pinia** - State management
- **Vue Router 4** - Client-side routing
- **Axios** - HTTP client

## Project Structure

```
src/
├── api/           # API client and services
├── components/    # Reusable Vue components
├── composables/   # Vue composition functions
├── router/        # Route configuration
├── stores/        # Pinia stores for state management
├── views/         # Page-level components
└── main.js        # Application entry point
```

## Key Features

- **Authentication**: JWT-based with automatic token refresh
- **Gene Management**: Browse, search, and manage genetic data
- **Role-Based Access**: Admin, curator, and viewer permissions
- **Responsive Design**: Mobile-friendly Material Design UI
- **Real-time Updates**: Reactive data with optimistic updates
- **Global Notifications**: Toast-style success/error messages

## Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint

# Fix linting issues
npm run lint --fix
```

## Environment Variables

Create a `.env` file:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Docker Development

Use with the main project's Docker setup:

```bash
# From project root
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## API Integration

The frontend communicates with the FastAPI backend at `/api/v1`:

- **Authentication**: `/api/v1/auth/*`
- **Genes**: `/api/v1/genes/*`
- **Health**: `/api/v1/health`

## State Management

Uses Pinia stores:

- **AuthStore**: User authentication and permissions
- **GenesStore**: Gene data and operations

## Routing

Protected routes require authentication:

- `/login` - Public login page
- `/genes` - Public gene browsing
- `/admin/*` - Requires curator/admin role
- `/profile` - Requires authentication

## Contributing

1. Follow Vue 3 Composition API patterns
2. Use TypeScript-style prop definitions
3. Implement responsive design with Vuetify
4. Add proper error handling and loading states
5. Write semantic, accessible HTML