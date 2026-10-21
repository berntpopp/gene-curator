<template>
  <v-container>
    <v-row>
      <v-col cols="12" md="8" class="mx-auto">
        <v-card class="pa-6">
          <div class="text-center mb-6">
            <v-img
              src="/img/logo.png"
              alt="Gene Curator Logo"
              width="120"
              aspect-ratio="1"
              class="mx-auto mb-4"
            />
            <h1 class="text-h3 mb-2">Gene Curator</h1>
            <p class="text-h6 text-medium-emphasis">Gene-disease curation in scoped teams</p>
          </div>

          <v-divider class="my-6" />

          <section class="mb-6">
            <h2 class="text-h5 mb-3">What it is for</h2>
            <p class="text-body-1 mb-4">
              Gene Curator supports curators who assess the evidence linking a gene to a disease.
              Curation is organised in scopes. Each scope has its own members, genes and review
              workflow, and every curation is checked by a second person before it becomes active.
            </p>
          </section>

          <section class="mb-6">
            <h2 class="text-h5 mb-3">Supported methodologies</h2>
            <p class="text-body-1 mb-4">
              Platform admins create curation schemas under Templates (/admin/schemas). A scope
              chooses its methodology by picking a workflow pair.
            </p>
            <ul class="text-body-1 ml-6">
              <li>ClinGen gene-disease validity curation (SOP v11)</li>
              <li>GenCC classification</li>
              <li>Custom schemas created by platform admins</li>
            </ul>
          </section>

          <section class="mb-6">
            <h2 class="text-h5 mb-3">Maintainers and contact</h2>
            <p class="text-body-1 mb-4">
              Gene Curator is developed by the Halbritter Laboratory. Report problems or ask
              questions by opening an issue on the GitHub repository.
            </p>
            <p class="text-body-1 mb-4">
              The project is released under the MIT license. There is no citation file yet; cite the
              GitHub repository URL.
            </p>
          </section>

          <div class="text-center">
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

<script setup lang="ts">
  // Static content component
</script>
