<template>
  <v-container>
    <v-row>
      <v-col cols="12" md="8" class="mx-auto">
        <v-card class="pa-6">
          <div class="text-center mb-6">
            <v-img
              src="/img/logo.png"
              alt="Gene Curator Logo"
              max-width="120"
              class="mx-auto mb-4"
            />
            <h1 class="text-h3 mb-2">Gene Curator</h1>
            <p class="text-h6 text-medium-emphasis">
              Advanced platform for genetic information curation and management
            </p>
          </div>

          <v-divider class="my-6" />

          <div class="mb-6">
            <h2 class="text-h5 mb-3">About the Project</h2>
            <p class="text-body-1 mb-4">
              Gene Curator is a sophisticated Vue.js-based platform for genetic information curation
              and management, featuring a multi-stage workflow system. The project has undergone a
              major architectural transformation to implement native ClinGen Standard Operating
              Procedure (SOP v11) compliance and migrate to a modern three-tier architecture.
            </p>
          </div>

          <div class="mb-6">
            <h2 class="text-h5 mb-3">Key Features</h2>
            <v-list>
              <v-list-item prepend-icon="mdi-certificate">
                <v-list-item-title>ClinGen SOP v11 Compliance</v-list-item-title>
                <v-list-item-subtitle>
                  Automated evidence scoring and summary generation
                </v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-database">
                <v-list-item-title>Modern Architecture</v-list-item-title>
                <v-list-item-subtitle>
                  PostgreSQL + FastAPI + Vue 3 with Docker deployment
                </v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-shield-check">
                <v-list-item-title>Scientific Integrity</v-list-item-title>
                <v-list-item-subtitle>
                  Immutable change logs and cryptographic content addressing
                </v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-account-group">
                <v-list-item-title>Role-Based Access Control</v-list-item-title>
                <v-list-item-subtitle>
                  Secure authentication with granular permissions
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </div>

          <div class="mb-6">
            <h2 class="text-h5 mb-3">Technology Stack</h2>
            <v-row>
              <v-col cols="12" md="6">
                <h3 class="text-h6 mb-2">Frontend</h3>
                <v-chip class="ma-1" variant="outlined">Vue 3</v-chip>
                <v-chip class="ma-1" variant="outlined">Vuetify 3</v-chip>
                <v-chip class="ma-1" variant="outlined">Vite</v-chip>
                <v-chip class="ma-1" variant="outlined">Pinia</v-chip>
              </v-col>
              <v-col cols="12" md="6">
                <h3 class="text-h6 mb-2">Backend</h3>
                <v-chip class="ma-1" variant="outlined">FastAPI</v-chip>
                <v-chip class="ma-1" variant="outlined">PostgreSQL</v-chip>
                <v-chip class="ma-1" variant="outlined">SQLAlchemy</v-chip>
                <v-chip class="ma-1" variant="outlined">Docker</v-chip>
              </v-col>
            </v-row>
          </div>

          <v-divider class="my-6" />

          <div class="text-center">
            <h2 class="text-h5 mb-3">Halbritter Lab</h2>
            <p class="text-body-1 mb-4">
              Developed by the Halbritter Laboratory for advancing genetic research and clinical
              applications.
            </p>
            <v-btn
              href="https://github.com/halbritter-lab/gene-curator"
              target="_blank"
              color="primary"
              prepend-icon="mdi-github"
            >
              View on GitHub
            </v-btn>
          </div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
  // Static content component
</script>
