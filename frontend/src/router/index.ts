import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { logService } from '@/services/logService'
import { TERMINOLOGY } from '@/config/terminology'
import { safeRedirect } from '@/utils/safeRedirect'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    icon?: string
    label?: string
    order?: number
    requiresAuth?: boolean
    requiresGuest?: boolean
    requiredRoles?: string[]
    showInMainMenu?: boolean
    showInUserMenu?: boolean
    /** Dropdown group the item belongs to, e.g. 'curation' or 'curationSetup' */
    showInDropdown?: string
  }
}

// Lazy-loaded components
const Home = () => import('@/views/Home.vue')
const Login = () => import('@/views/Login.vue')
const Register = () => import('@/views/Register.vue')
const MyWork = () => import('@/views/MyWork.vue')
const ScopeList = () => import('@/views/scope/ScopeList.vue')
const ScopeCreate = () => import('@/views/scope/ScopeCreate.vue')
const ScopeDashboard = () => import('@/views/scope/ScopeDashboard.vue')
const GeneCatalogueView = () => import('@/views/GeneCatalogueView.vue')
const GenesTable = () => import('@/views/GenesTable.vue')
const GeneDetail = () => import('@/views/GeneDetail.vue')
const GeneAssignments = () => import('@/views/GeneAssignments.vue')
const AssignmentDetail = () => import('@/views/AssignmentDetail.vue')
const SchemaManagement = () => import('@/views/SchemaManagement.vue')
const SchemaEditor = () => import('@/views/SchemaEditor.vue')
const WorkflowManagement = () => import('@/views/WorkflowManagement.vue')
const UserProfile = () => import('@/views/UserProfile.vue')
const UserManagement = () => import('@/views/UserManagement.vue')
const About = () => import('@/views/About.vue')
const FAQ = () => import('@/views/FAQ.vue')
const NotAuthorized = () => import('@/views/NotAuthorized.vue')
const NotFound = () => import('@/views/NotFound.vue')
const GeneSummaryView = () => import('@/views/GeneSummaryView.vue')
const CurationFormView = () => import('@/views/curation/CurationFormView.vue')
const CurationDetailView = () => import('@/views/curation/CurationDetailView.vue')
const PrecurationFormView = () => import('@/views/curation/PrecurationFormView.vue')
const ReviewQueueView = () => import('@/views/curation/ReviewQueueView.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: Home,
    // Signed-in users land on My work; Home is the public landing page
    beforeEnter: () => (useAuthStore().isAuthenticated ? { name: 'MyWork' } : true),
    meta: {
      title: 'Gene Curator'
    }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: {
      title: TERMINOLOGY.SIGN_IN,
      requiresGuest: true
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: {
      title: 'Register',
      requiresGuest: true
    }
  },
  {
    path: '/my-work',
    name: 'MyWork',
    component: MyWork,
    meta: {
      title: 'My work',
      requiresAuth: true,
      showInMainMenu: true,
      icon: 'mdi-clipboard-list',
      label: 'My work',
      order: 1
    }
  },
  // The dashboard is replaced by My work; keep the old URL and route name working
  { path: '/dashboard', name: 'Dashboard', redirect: { name: 'MyWork' } },
  {
    path: '/scopes',
    name: 'scopes',
    component: ScopeList,
    meta: {
      title: TERMINOLOGY.SCOPES,
      requiresAuth: true,
      showInMainMenu: true,
      icon: 'mdi-folder-multiple',
      label: TERMINOLOGY.SCOPES,
      order: 3,
      tabOrder: 4
    }
  },
  {
    path: '/scopes/create',
    name: 'scope-create',
    component: ScopeCreate,
    meta: {
      title: 'Create Scope',
      requiresAuth: true
      // Any authenticated user can create a scope
    }
  },
  {
    path: '/scopes/:scopeId/:tab?',
    name: 'scope-dashboard',
    component: ScopeDashboard,
    props: true,
    meta: {
      title: 'Scope Dashboard',
      requiresAuth: true
    }
  },
  // Review Queue (cross-scope)
  {
    path: '/review-queue',
    name: 'review-queue',
    component: ReviewQueueView,
    meta: {
      title: 'Review Queue',
      requiresAuth: true,
      showInMainMenu: true,
      icon: 'mdi-clipboard-check-outline',
      label: 'Review',
      order: 2
    }
  },
  // Curation routes
  {
    path: '/scopes/:scopeId/curations/new',
    name: 'curation-create',
    component: CurationFormView,
    props: true,
    meta: {
      title: 'New Curation',
      requiresAuth: true
    }
  },
  {
    path: '/scopes/:scopeId/curations/:curationId',
    name: 'curation-detail',
    component: CurationDetailView,
    props: true,
    meta: {
      title: 'Curation Details',
      requiresAuth: true
    }
  },
  {
    path: '/scopes/:scopeId/curations/:curationId/edit',
    name: 'curation-edit',
    component: CurationFormView,
    props: true,
    meta: {
      title: 'Edit Curation',
      requiresAuth: true
    }
  },
  {
    path: '/scopes/:scopeId/genes/:geneId/curation/new',
    name: 'gene-curation-create',
    component: CurationFormView,
    props: true,
    meta: {
      title: 'New Gene Curation',
      requiresAuth: true
    }
  },
  {
    path: '/scopes/:scopeId/precurations/:precurationId',
    name: 'precuration-edit',
    component: PrecurationFormView,
    props: true,
    meta: {
      title: 'Precuration',
      requiresAuth: true
    }
  },
  {
    path: '/scopes/:scopeId/genes/:geneId/precuration/new',
    name: 'gene-precuration-create',
    component: PrecurationFormView,
    props: true,
    meta: {
      title: 'New Precuration',
      requiresAuth: true
    }
  },
  {
    path: '/genes',
    name: 'GeneCatalogue',
    component: GeneCatalogueView,
    meta: {
      title: TERMINOLOGY.GENE_CATALOG,
      requiresAuth: false,
      showInMainMenu: true,
      icon: 'mdi-dna',
      label: TERMINOLOGY.GENE_CATALOG,
      tabLabel: 'Genes',
      tabOrder: 3,
      order: 4
    }
  },
  {
    path: '/admin/genes',
    name: 'GeneAdmin',
    component: GenesTable,
    meta: {
      title: TERMINOLOGY.GENES,
      requiresAuth: true,
      requiredRoles: ['admin'],
      showInDropdown: 'curationSetup',
      icon: 'mdi-dna',
      label: TERMINOLOGY.GENES,
      order: 4
    }
  },
  {
    path: '/genes/:id',
    name: 'GeneDetail',
    component: GeneDetail,
    props: true,
    meta: {
      title: 'Gene Details',
      requiresAuth: false
    }
  },
  {
    path: '/genes/:geneId/summary',
    name: 'GeneSummary',
    component: GeneSummaryView,
    props: true,
    meta: {
      title: 'Gene Summary',
      requiresAuth: false
    }
  },
  {
    path: '/assignments',
    name: 'GeneAssignments',
    component: GeneAssignments,
    meta: {
      title: 'Assignments',
      requiresAuth: true
    }
  },
  {
    path: '/assignments/:id',
    name: 'AssignmentDetail',
    component: AssignmentDetail,
    props: true,
    meta: {
      title: 'Assignment Details',
      requiresAuth: true
    }
  },
  {
    path: '/admin/schemas',
    name: 'SchemaManagement',
    component: SchemaManagement,
    meta: {
      title: TERMINOLOGY.TEMPLATES,
      requiresAuth: true,
      requiredRoles: ['admin'],
      showInDropdown: 'curationSetup',
      icon: 'mdi-file-document-outline',
      label: TERMINOLOGY.TEMPLATES,
      order: 1
    }
  },
  {
    path: '/admin/schemas/:id/edit',
    name: 'SchemaEditor',
    component: SchemaEditor,
    props: true,
    meta: {
      title: 'Schema Editor',
      requiresAuth: true,
      requiredRoles: ['admin']
    }
  },
  {
    path: '/admin/workflows',
    name: 'WorkflowManagement',
    component: WorkflowManagement,
    meta: {
      title: TERMINOLOGY.WORKFLOWS,
      requiresAuth: true,
      requiredRoles: ['admin'],
      showInDropdown: 'curationSetup',
      icon: 'mdi-sitemap-outline',
      label: TERMINOLOGY.WORKFLOWS,
      order: 2
    }
  },
  {
    path: '/profile',
    name: 'UserProfile',
    component: UserProfile,
    meta: {
      title: 'User Profile',
      requiresAuth: true,
      showInUserMenu: true,
      icon: 'mdi-account',
      label: 'Profile',
      order: 2
    }
  },
  {
    path: '/admin/users',
    name: 'UserManagement',
    component: UserManagement,
    meta: {
      title: 'User Management',
      requiresAuth: true,
      requiredRoles: ['admin'],
      showInDropdown: 'curationSetup',
      icon: 'mdi-account-group',
      label: 'Users',
      order: 3
    }
  },
  {
    path: '/about',
    name: 'About',
    component: About,
    meta: { title: 'About' }
  },
  {
    path: '/faq',
    name: 'FAQ',
    component: FAQ,
    meta: { title: 'FAQ' }
  },
  {
    path: '/not-authorized',
    name: 'NotAuthorized',
    component: NotAuthorized,
    meta: { title: 'Not Authorized' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFound,
    meta: { title: 'Page Not Found' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// Navigation guards
router.beforeEach(async to => {
  const authStore = useAuthStore()

  // Initialize auth store if not already done
  if (!authStore.isAuthenticated && authStore.token) {
    try {
      await authStore.initialize()
    } catch (err) {
      const error = err as Error
      logService.warn('Auth initialization failed', {
        error: error.message,
        stack: error.stack
      })
    }
  }

  // Update document title
  document.title = to.meta.title ? `${to.meta.title} | Gene Curator` : 'Gene Curator'

  // Handle guest-only routes (login, register)
  if (to.meta.requiresGuest && authStore.isAuthenticated) {
    // Honour ?redirect= only for same-origin paths
    return safeRedirect(to.query.redirect) ?? { name: 'Home' }
  }

  // Handle protected routes
  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      return { name: 'Login', query: { redirect: to.fullPath } }
    }

    // Check role requirements
    if (to.meta.requiredRoles) {
      const hasRequiredRole = to.meta.requiredRoles.some(role => authStore.hasRole(role))
      if (!hasRequiredRole) {
        return { name: 'NotAuthorized', query: { redirect: to.fullPath } }
      }
    }
  }

  return true
})

export default router
