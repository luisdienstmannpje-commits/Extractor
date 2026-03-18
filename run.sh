#!/usr/bin/env bash
# Redireciona para o backend oficial (smart-extractor)
exec "$(dirname "$0")/smart-extractor/run.sh" "$@"
