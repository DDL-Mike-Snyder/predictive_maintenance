{{/*
09-monorepo-and-conventions.md §4.4: every per-service chart depends on this
library chart for name/label templates, so `fathom.navy/service` -- the
label NetworkPolicy peer selectors match on (§4.4.2) -- is identical across
every service's Deployment, Service, and NetworkPolicy, keyed off the
canonical `slug` in values.yaml, not a release-name-derived value.
*/}}

{{- define "fathom.name" -}}
{{- .Values.slug | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "fathom.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Values.slug | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "fathom.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Stable across upgrades -- used for both pod-template labels AND
Service/NetworkPolicy selectors, which must never change once set.
*/}}
{{- define "fathom.selectorLabels" -}}
app.kubernetes.io/name: {{ include "fathom.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
fathom.navy/service: {{ .Values.slug }}
{{- end -}}

{{- define "fathom.labels" -}}
{{ include "fathom.selectorLabels" . }}
helm.sh/chart: {{ include "fathom.chart" . }}
app.kubernetes.io/part-of: fathom
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
{{- end -}}
