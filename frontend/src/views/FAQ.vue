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
    }
  ]
</script>
