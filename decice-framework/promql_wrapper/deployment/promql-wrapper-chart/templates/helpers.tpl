{{- define "sha256sum" -}}
{{- printf "%s" . | sha256sum -}}
{{- end }}
