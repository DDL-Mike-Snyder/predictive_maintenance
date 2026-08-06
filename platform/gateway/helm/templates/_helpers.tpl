{{/*
Gateway has no named templates of its own for name/label purposes --
fathom.name / fathom.fullname / fathom.chart / fathom.labels /
fathom.selectorLabels all come from the _fathom-common library chart
dependency (09-monorepo-and-conventions.md §4.4, Chart.yaml), identical to
services/pdm/helm's own use of it. The one helper below is gateway-local
only because it depends on Values.image, which _fathom-common has no
opinion on: it's shared between deployment.yaml and migration-job.yaml
(same image, same shape as services/pdm/helm's own "pdm.image" helper),
not because it belongs in the common chart.
*/}}

{{/*
Image reference: digest wins when CI has set one (immutable, promoted
across environments per 09 §4.3); tag is local-dev-only fallback.
*/}}
{{- define "gateway.image" -}}
{{- if .Values.image.digest -}}
{{- printf "%s@%s" .Values.image.repository .Values.image.digest -}}
{{- else -}}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default "latest") -}}
{{- end -}}
{{- end -}}
