<template>
  <v-container>
    <v-row>
      <v-col cols="12" md="10" class="mx-auto">
        <h1 class="text-h4 mb-6">Frequently Asked Questions</h1>

        <v-expansion-panels variant="accordion">
          <v-expansion-panel v-for="(faq, index) in faqs" :key="index">
            <v-expansion-panel-title>
              {{ faq.question }}
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <div v-html="faq.answer"></div>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
  const faqs = [
    {
      question: 'What is Gene Curator?',
      answer:
        'Gene Curator is an advanced platform for genetic information curation and management, designed to support ClinGen Standard Operating Procedures v11 with automated evidence scoring and summary generation.'
    },
    {
      question: 'Who can use Gene Curator?',
      answer:
        'Gene Curator supports three user roles:<br/>• <strong>Viewers</strong>: Can browse and search gene information<br/>• <strong>Curators</strong>: Can add, edit, and manage gene data<br/>• <strong>Administrators</strong>: Full system access including user management'
    },
    {
      question: 'How do I get access?',
      answer:
        "Contact your system administrator to request an account. New users are assigned the 'viewer' role by default and can be upgraded to curator or admin roles as needed."
    },
    {
      question: 'What is ClinGen compliance?',
      answer:
        'ClinGen (Clinical Genome Resource) provides standardized procedures for gene-disease validity curation. Gene Curator implements SOP v11 with automated evidence scoring and template-driven summary generation.'
    },
    {
      question: 'How do I search for genes?',
      answer:
        'Use the search functionality on the Genes page to find genes by:<br/>• Gene symbol (approved, previous, or alias)<br/>• HGNC ID<br/>• Gene family<br/>• Chromosome location<br/>• Keywords in gene descriptions'
    },
    {
      question: 'Can I import multiple genes at once?',
      answer:
        'Yes, curators and administrators can use the bulk import feature in Gene Administration to upload multiple genes from CSV files or paste data directly.'
    },
    {
      question: 'What data is stored for each gene?',
      answer:
        'Gene Curator stores comprehensive genetic information including:<br/>• Basic identifiers (HGNC ID, symbols)<br/>• Chromosomal location<br/>• Gene families and classifications<br/>• ClinGen scores and metrics<br/>• External database references<br/>• Change history and provenance'
    },
    {
      question: 'Is my data secure?',
      answer:
        'Yes, Gene Curator implements multiple security measures:<br/>• JWT-based authentication<br/>• Role-based access control<br/>• Encrypted data transmission<br/>• Audit logs for all changes<br/>• Cryptographic content addressing for data integrity'
    },
    {
      question: 'How do I precurate a gene?',
      answer:
        'To precurate a gene:<br/>1. Navigate to your scope and find the assigned gene<br/>2. Click "Start Precuration" to open the dynamic form<br/>3. Fill in the precuration fields (disease association, lumping/splitting decision, etc.)<br/>4. Save as draft or submit to advance the gene to the curation stage'
    },
    {
      question: 'How does the review workflow work?',
      answer:
        'Gene Curator uses a 4-eyes principle for quality assurance:<br/>1. A curator submits their curation for review<br/>2. A different user (reviewer or admin) is assigned to review<br/>3. The reviewer can approve, request changes, or reject<br/>4. On approval, the curation becomes active<br/><br/>The same person who created a curation cannot approve it.'
    },
    {
      question: 'What happens when a curation is rejected?',
      answer:
        'When a reviewer rejects or requests changes:<br/>• The curator receives a notification<br/>• The curation returns to the curation stage<br/>• The curator can edit and resubmit<br/>• Review comments are preserved for reference'
    },
    {
      question: 'Can I work across multiple scopes?',
      answer:
        'Yes. You can be a member of multiple scopes with different roles in each. For example, you might be a curator in "Kidney Genetics" and a reviewer in "Cardiac Genetics". Use the scope selector in the navigation to switch between your active scopes.'
    },
    {
      question: 'How do I manage gene assignments as an admin?',
      answer:
        'Scope admins can manage gene assignments from the Gene Assignment Manager:<br/>• <strong>View</strong>: See assignment details, history, and current status<br/>• <strong>Edit</strong>: Change priority, due date, and notes<br/>• <strong>Reassign</strong>: Transfer a gene to a different curator within the scope'
    },
    {
      question: 'Where do I see my notifications?',
      answer:
        'Notifications appear in the bell icon in the top navigation bar. The badge shows your unread count. Click to see all notifications including review assignments, approvals, rejections, and revision requests. You can mark individual notifications or all as read.'
    }
  ]
</script>
