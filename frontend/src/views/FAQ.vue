<template>
  <v-container>
    <v-row>
      <v-col cols="12" md="10" class="mx-auto">
        <h1 class="text-headline-large mb-6">Frequently Asked Questions</h1>

        <v-expansion-panels variant="accordion">
          <v-expansion-panel v-for="faq in faqs" :id="faq.id" :key="faq.id">
            <v-expansion-panel-title>
              {{ faq.question }}
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <p>{{ faq.answer }}</p>
              <ul v-if="faq.items" class="ml-6 mt-2">
                <li v-for="item in faq.items" :key="item">{{ item }}</li>
              </ul>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
  interface Faq {
    id: string
    question: string
    answer: string
    items?: string[]
  }

  const faqs: Faq[] = [
    {
      id: 'what-is-gene-curator',
      question: 'What is Gene Curator?',
      answer:
        'Gene Curator is a platform for gene-disease curation. Curation is organised in scopes, each with its own members, genes and workflow. Curation follows a configurable schema, for example the ClinGen SOP or GenCC.'
    },
    {
      id: 'roles',
      question: 'What roles exist?',
      answer:
        'There are two separate role systems. Your account role is either admin (platform administration) or user. Inside each scope you hold one of these roles:',
      items: [
        'Admin: manages the scope, its members and workflow',
        'Curator: prepares precurations and curations for assigned genes',
        'Reviewer: reviews curations submitted by others (4-eyes principle)',
        'Viewer: read-only access to the scope'
      ]
    },
    {
      id: 'clingen-classification',
      question: 'How does the ClinGen SOP classification work?',
      answer:
        'The evidence score sets the classification. Limited is 1 to 6 points, Moderate 7 to 11 points and Strong 12 to 18 points. Definitive requires Strong-level points plus replication over time, with no contradictory evidence. Contradictory evidence gives Disputed.'
    },
    {
      id: 'get-access',
      question: 'How do I get access?',
      answer:
        'Register an account from the Register page. Access to a scope is granted when a scope admin invites you as a member. Pending invitations do not grant access until you accept them.'
    },
    {
      id: 'search-genes',
      question: 'How do I search for genes?',
      answer:
        'Open the Gene Catalogue (/genes) and use the "Search genes" field. It matches gene symbols and HGNC IDs. You can narrow the results with the Classification, Disease and Scope filters.'
    },
    {
      id: 'bulk-add-genes',
      question: 'Can I add several genes at once?',
      answer:
        'Yes. In the Add Genes dialog, switch to the bulk tab and enter gene symbols or HGNC IDs, one per line or comma-separated. Validate the list before adding. Files cannot be uploaded.'
    },
    {
      id: 'precurate-gene',
      question: 'How do I precurate a gene?',
      answer:
        'Open your scope and find the gene assigned to you, then choose Start Precuration. Fill in the precuration form and save it as a draft, or submit it when it is complete. Once a reviewer approves the precuration, the curation draft is created automatically.'
    },
    {
      id: 'review-workflow',
      question: 'How does the review workflow work?',
      answer:
        'Submitted precurations and curations wait in the Review Queue (/review-queue), which is in the main menu and shows a count of items to review. A reviewer in the same scope approves the item, requests changes, or rejects it. Approval makes a curation active. The person who created an item cannot review it, so a second person must approve it.'
    },
    {
      id: 'requested-changes',
      question: 'What happens when changes are requested or a curation is rejected?',
      answer:
        'The feedback entered by the reviewer is shown to the curator. A curation that needs changes can be revised and resubmitted. A rejected curation is marked as rejected.'
    },
    {
      id: 'multiple-scopes',
      question: 'Can I work in more than one scope?',
      answer:
        'Yes. You can be a member of several scopes with a different role in each. Open each scope from the Scopes page.'
    },
    {
      id: 'assignments',
      question: 'Where are gene assignments managed?',
      answer:
        'My Work (/assignments) lists only the genes assigned to you. The All assignments table is for platform admins and scope admins. There you can edit an assignment, which changes its priority, due date and notes, or reassign a gene to another curator in the scope.'
    },
    {
      id: 'notifications',
      question: 'Where do I see notifications?',
      answer:
        'An unread count badge appears on your account button in the top bar. It shows how many notifications are unread.'
    }
  ]
</script>
