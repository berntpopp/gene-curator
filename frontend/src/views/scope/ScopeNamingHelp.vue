<template>
  <v-card class="mt-4">
    <v-card-title>
      <v-icon start>mdi-help-circle</v-icon>
      Scope naming guidelines
    </v-card-title>
    <v-card-text>
      <v-list density="compact">
        <v-list-item>
          <template #prepend>
            <v-icon icon="mdi-check" color="success"></v-icon>
          </template>
          <v-list-item-title> Use lowercase letters (a-z) </v-list-item-title>
        </v-list-item>

        <v-list-item>
          <template #prepend>
            <v-icon icon="mdi-check" color="success"></v-icon>
          </template>
          <v-list-item-title> Separate words with dashes (-) </v-list-item-title>
        </v-list-item>

        <v-list-item>
          <template #prepend>
            <v-icon icon="mdi-check" color="success"></v-icon>
          </template>
          <v-list-item-title> Length: 4-64 characters </v-list-item-title>
        </v-list-item>

        <v-list-item>
          <template #prepend>
            <v-icon icon="mdi-close" color="error"></v-icon>
          </template>
          <v-list-item-title> No consecutive dashes (--) </v-list-item-title>
        </v-list-item>

        <v-list-item>
          <template #prepend>
            <v-icon icon="mdi-close" color="error"></v-icon>
          </template>
          <v-list-item-title> No spaces or special characters </v-list-item-title>
        </v-list-item>
      </v-list>

      <v-divider class="my-2" />

      <div class="text-caption text-medium-emphasis">
        <strong>Examples:</strong>
        <ul>
          <li>kidney-genetics</li>
          <li>cardio-genetics</li>
          <li>neuro-oncology</li>
        </ul>
      </div>
    </v-card-text>
  </v-card>
</template>
