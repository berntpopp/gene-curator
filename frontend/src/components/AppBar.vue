<template>
  <v-app-bar app color="primary" dark>
    <!-- Logo Image -->
    <v-img
      src="/img/logo.png"
      class="mr-3 app-logo"
      contain
      max-height="48"
      max-width="48"
      @click="$router.push('/')"
    />

    <!-- Toolbar Title -->
    <v-toolbar-title>
      <span class="clickable" @click="$router.push('/')"> Gene Curator </span>
      <br />
      <span class="version-info"> Version: {{ version }} - Build: {{ buildHash }} </span>
    </v-toolbar-title>

    <v-spacer />

    <!-- Navigation Menu -->
    <template v-for="item in visibleMenuItems" :key="item.name">
      <v-menu v-if="item.children" offset-y>
        <template #activator="{ props }">
          <v-btn text v-bind="props">
            <v-icon v-if="item.icon" start>{{ item.icon }}</v-icon>
            {{ item.title }}
          </v-btn>
        </template>
        <v-list>
          <v-list-item v-for="child in item.children" :key="child.name" :to="child.to">
            <template v-if="child.icon" #prepend>
              <v-icon>{{ child.icon }}</v-icon>
            </template>
            <v-list-item-title>{{ child.title }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-btn v-else :to="item.to" text>
        <v-icon v-if="item.icon" start>{{ item.icon }}</v-icon>
        {{ item.title }}
      </v-btn>
    </template>

    <!-- Theme Toggle -->
    <v-btn icon @click="toggleTheme">
      <v-icon>
        {{ isDark ? 'mdi-weather-night' : 'mdi-white-balance-sunny' }}
      </v-icon>
    </v-btn>

    <!-- User Menu -->
    <template v-if="authStore.isAuthenticated">
      <v-menu offset-y>
        <template #activator="{ props }">
          <v-btn icon v-bind="props">
            <v-avatar size="32">
              <v-icon>mdi-account-circle</v-icon>
            </v-avatar>
          </v-btn>
        </template>
        <v-list>
          <v-list-item>
            <v-list-item-title>{{ authStore.user?.email }}</v-list-item-title>
            <v-list-item-subtitle>{{ authStore.user?.role }}</v-list-item-subtitle>
          </v-list-item>
          <v-divider />
          <v-list-item :to="{ name: 'UserProfile' }">
            <template #prepend>
              <v-icon>mdi-account</v-icon>
            </template>
            <v-list-item-title>Profile</v-list-item-title>
          </v-list-item>
          <v-list-item @click="handleLogout">
            <template #prepend>
              <v-icon>mdi-logout</v-icon>
            </template>
            <v-list-item-title>Logout</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </template>

    <!-- Login Button -->
    <v-btn v-else icon :to="{ name: 'Login' }">
      <v-icon>mdi-login</v-icon>
    </v-btn>
  </v-app-bar>
</template>

<script setup>
import { useLogger } from '@/composables/useLogger'

const logger = useLogger()
  import { ref, computed, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { useTheme } from 'vuetify'
  import { useAuthStore } from '@/stores/auth.js'

  const router = useRouter()
  const theme = useTheme()
  const authStore = useAuthStore()

  // Version info
  const version = ref('0.3.0')
  const buildHash = ref('dev')

  // Theme
  const isDark = computed(() => theme.global.current.value.dark)

  // Menu configuration
  const menuItems = [
    {
      name: 'home',
      title: 'Home',
      to: { name: 'Home' },
      icon: 'mdi-home',
      requiresAuth: false
    },
    {
      name: 'dashboard',
      title: 'Dashboard',
      to: { name: 'Dashboard' },
      icon: 'mdi-view-dashboard',
      requiresAuth: true
    },
    {
      name: 'genes',
      title: 'Genes',
      to: { name: 'Genes' },
      icon: 'mdi-dna',
      requiresAuth: false
    },
    {
      name: 'curation',
      title: 'Curation',
      icon: 'mdi-clipboard-check',
      requiresAuth: true,
      requiredRoles: ['admin', 'curator'],
      children: [
        {
          name: 'assignments',
          title: 'Gene Assignments',
          to: { name: 'GeneAssignments' },
          icon: 'mdi-account-group'
        },
        {
          name: 'new-assignment',
          title: 'New Assignment',
          to: { name: 'ScopeSelection' },
          icon: 'mdi-plus-circle'
        },
        {
          name: 'validation',
          title: 'Validation Dashboard',
          to: { name: 'ValidationDashboard' },
          icon: 'mdi-check-decagram'
        }
      ]
    },
    {
      name: 'admin',
      title: 'Admin',
      icon: 'mdi-cog',
      requiresAuth: true,
      requiredRoles: ['admin'],
      children: [
        {
          name: 'schemas',
          title: 'Schema Management',
          to: { name: 'SchemaManagement' },
          icon: 'mdi-file-document-outline',
          requiredRoles: ['admin']
        },
        {
          name: 'workflows',
          title: 'Workflow Management',
          to: { name: 'WorkflowManagement' },
          icon: 'mdi-workflow',
          requiredRoles: ['admin']
        },
        {
          name: 'user-management',
          title: 'User Management',
          to: { name: 'UserManagement' },
          icon: 'mdi-account-group',
          requiredRoles: ['admin']
        }
      ]
    },
    {
      name: 'help',
      title: 'Help',
      icon: 'mdi-help-circle',
      children: [
        {
          name: 'about',
          title: 'About',
          to: { name: 'About' },
          icon: 'mdi-information'
        },
        {
          name: 'faq',
          title: 'FAQ',
          to: { name: 'FAQ' },
          icon: 'mdi-frequently-asked-questions'
        }
      ]
    }
  ]

  // Computed menu items based on auth state
  const visibleMenuItems = computed(() => {
    return menuItems
      .map(item => ({
        ...item,
        children: item.children ? [...item.children] : undefined
      }))
      .filter(item => {
        // Check auth requirements
        if (item.requiresAuth && !authStore.isAuthenticated) {
          return false
        }

        // Check role requirements
        if (item.requiredRoles && !authStore.hasAnyRole(item.requiredRoles)) {
          return false
        }

        // Filter children based on role requirements
        if (item.children) {
          item.children = item.children.filter(child => {
            if (child.requiredRoles && !authStore.hasAnyRole(child.requiredRoles)) {
              return false
            }
            return true
          })

          // Hide parent if no children are visible
          if (item.children.length === 0) {
            return false
          }
        }

        return true
      })
  })

  const toggleTheme = () => {
    // Use the modern Vuetify 3.9+ theme API
    theme.toggle()
    const newTheme = theme.global.current.value.dark ? 'dark' : 'light'
    localStorage.setItem('theme', newTheme)
  }

  const handleLogout = async () => {
    try {
      await authStore.logout()
      router.push({ name: 'Home' })
    } catch (error) {
      logger.error('Logout error:', { error: error.message, stack: error.stack })
    }
  }

  onMounted(() => {
    // Apply saved theme on mount using modern Vuetify 3.9+ API
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme && theme.global.name.value !== savedTheme) {
      theme.change(savedTheme)
    }
  })
</script>

<style scoped>
  .app-logo {
    cursor: pointer;
    transition: transform 0.2s ease;
  }

  .app-logo:hover {
    transform: scale(1.05);
  }

  .clickable {
    cursor: pointer;
    transition: opacity 0.2s ease;
  }

  .clickable:hover {
    opacity: 0.8;
  }

  .version-info {
    font-size: 0.75rem;
    opacity: 0.7;
    line-height: 1;
    margin-top: -4px;
  }
</style>
