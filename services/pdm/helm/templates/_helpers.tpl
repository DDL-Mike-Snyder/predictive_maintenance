{{/*
PdM has no named templates of its own for name/label purposes -- fathom.name
/ fathom.fullname / fathom.chart / fathom.labels / fathom.selectorLabels all
come from the _fathom-common library chart dependency
(09-monorepo-and-conventions.md §4.4, Chart.yaml). The one helper below is
PdM-local only because it depends on Values.image, which _fathom-common has
no opinion on: it's shared between deployment.yaml and migration-job.yaml
(same image, §4.2's migration-job.yaml note), not because it belongs in the
common chart.
*/}}

{{/*
Image reference: digest wins when CI has set one (immutable, promoted
across environments per 09 §4.3); tag is local-dev-only fallback.
*/}}
{{- define "pdm.image" -}}
{{- if .Values.image.digest -}}
{{- printf "%s@%s" .Values.image.repository .Values.image.digest -}}
{{- else -}}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default "latest") -}}
{{- end -}}
{{- end -}}
