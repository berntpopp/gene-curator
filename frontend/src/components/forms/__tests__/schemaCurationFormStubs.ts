export const stubs = {
  ErrorBoundary: { name: 'ErrorBoundary', template: '<div><slot /></div>' },
  // Renders the form's component sections like the real one does
  DynamicForm: {
    name: 'DynamicForm',
    props: {
      definition: Object,
      methodologyVersionId: String,
      initialData: Object,
      hideScoring: Boolean
    },
    template:
      '<div><slot name="section" :section="{ component: \'ScoreSummary\' }" /><slot name="section" :section="{ component: \'LumpingSplittingSection\' }" /></div>'
  },
  ScoreSummary: {
    name: 'ScoreSummary',
    props: ['scores', 'classification'],
    template: '<i />'
  },
  LumpingSplittingSection: {
    name: 'LumpingSplittingSection',
    props: ['precurationData'],
    template: '<i />'
  },
  FormActions: true,
  FormRecoveryDialog: true
}
