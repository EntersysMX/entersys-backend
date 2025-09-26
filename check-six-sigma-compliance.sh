#!/bin/bash
# 🎯 SCRIPT DE VERIFICACIÓN SIX SIGMA COMPLIANCE - ENTERSYS
# Validación automática de SLA y métricas de calidad
# Versión: 1.0.0

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Variables de configuración
PROMETHEUS_URL="https://monitoring.entersys.mx:9090"
GRAFANA_URL="https://monitoring.entersys.mx"
SIX_SIGMA_AVAILABILITY=0.9999966  # 99.99966%
SIX_SIGMA_RESPONSE_TIME=3         # 3 segundos
SIX_SIGMA_ERROR_RATE=0.00034      # 0.00034%

PERIOD=${1:-"24h"}  # Período de análisis (24h, 7d, 30d)
FORMAT=${2:-"table"}  # Formato de salida (table, json, summary)

# Función para mostrar ayuda
show_help() {
    echo -e "${BLUE}🎯 VERIFICACIÓN SIX SIGMA COMPLIANCE - ENTERSYS${NC}"
    echo "=================================================="
    echo ""
    echo "Uso: $0 [período] [formato]"
    echo ""
    echo "Parámetros:"
    echo "  período : Período de análisis (24h, 7d, 30d) - default: 24h"
    echo "  formato : Formato de salida (table, json, summary) - default: table"
    echo ""
    echo "Ejemplos:"
    echo "  $0                    # Análisis últimas 24h en formato tabla"
    echo "  $0 7d                 # Análisis últimos 7 días"
    echo "  $0 24h json           # Análisis 24h en formato JSON"
    echo "  $0 30d summary        # Resumen ejecutivo 30 días"
    echo ""
    echo -e "${YELLOW}Estándares Six Sigma:${NC}"
    echo "  📈 Disponibilidad: >= 99.99966% (3.4 defectos por millón)"
    echo "  ⚡ Tiempo respuesta P95: <= 3.0 segundos"
    echo "  🚨 Tasa de errores: <= 0.00034%"
    echo ""
    exit 1
}

if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    show_help
fi

# Función para log con colores
log_header() {
    echo -e "${PURPLE}$1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

# Función para hacer queries a Prometheus
prometheus_query() {
    local query="$1"
    local encoded_query=$(printf '%s\n' "$query" | jq -sRr @uri)
    curl -s "$PROMETHEUS_URL/api/v1/query?query=$encoded_query" | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "0"
}

prometheus_query_range() {
    local query="$1"
    local period="$2"
    local encoded_query=$(printf '%s\n' "$query" | jq -sRr @uri)
    curl -s "$PROMETHEUS_URL/api/v1/query?query=$encoded_query" 2>/dev/null || echo '{"data":{"result":[]}}'
}

# Función para obtener lista de servicios
get_services() {
    curl -s "$PROMETHEUS_URL/api/v1/label/job/values" 2>/dev/null | jq -r '.data[]' | grep -E "(blackbox|app|api)" | head -20
}

# Función para validar conectividad
validate_connectivity() {
    log_info "Validando conectividad con Prometheus..."

    if ! curl -s "$PROMETHEUS_URL/-/healthy" >/dev/null 2>&1; then
        log_error "No se puede conectar a Prometheus en $PROMETHEUS_URL"
        log_error "Verifica que el servicio esté ejecutándose y sea accesible"
        exit 1
    fi

    log_success "Conectividad con Prometheus validada"
}

# Función para calcular compliance score
calculate_compliance_score() {
    local availability=$1
    local response_time=$2
    local error_rate=$3

    local avail_score=0
    local resp_score=0
    local error_score=0

    # Scoring de disponibilidad
    if (( $(echo "$availability >= $SIX_SIGMA_AVAILABILITY" | bc -l) )); then
        avail_score=100
    else
        avail_score=$(echo "scale=2; $availability / $SIX_SIGMA_AVAILABILITY * 100" | bc -l)
    fi

    # Scoring de tiempo de respuesta
    if (( $(echo "$response_time <= $SIX_SIGMA_RESPONSE_TIME" | bc -l) )); then
        resp_score=100
    else
        resp_score=$(echo "scale=2; $SIX_SIGMA_RESPONSE_TIME / $response_time * 100" | bc -l)
        if (( $(echo "$resp_score > 100" | bc -l) )); then
            resp_score=100
        fi
    fi

    # Scoring de tasa de errores
    if (( $(echo "$error_rate <= $SIX_SIGMA_ERROR_RATE" | bc -l) )); then
        error_score=100
    else
        error_score=$(echo "scale=2; $SIX_SIGMA_ERROR_RATE / $error_rate * 100" | bc -l)
        if (( $(echo "$error_score > 100" | bc -l) )); then
            error_score=100
        fi
    fi

    # Score total (promedio ponderado)
    local total_score=$(echo "scale=2; ($avail_score * 0.4 + $resp_score * 0.4 + $error_score * 0.2)" | bc -l)
    echo "$total_score"
}

# Banner principal
clear
echo -e "${BLUE}"
echo "🎯 =============================================="
echo "   SIX SIGMA COMPLIANCE VERIFICATION"
echo "   Sistema de Monitoreo EnterSys"
echo "   Período: $PERIOD | Formato: $FORMAT"
echo "=============================================="
echo -e "${NC}"

# Validar conectividad
validate_connectivity

# Obtener timestamp del análisis
ANALYSIS_TIME=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
ANALYSIS_TIMESTAMP=$(date +%s)

log_header "📊 INICIANDO ANÁLISIS SIX SIGMA..."
echo ""

# Arrays para almacenar resultados
declare -A services_data
declare -a compliant_services
declare -a non_compliant_services
declare -A service_scores

# Obtener lista de endpoints monitoreados
log_info "Obteniendo lista de servicios monitoreados..."

# Obtener todos los targets de blackbox (health checks)
HEALTH_ENDPOINTS=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=probe_success" 2>/dev/null | jq -r '.data.result[].metric.instance' | sort | uniq)

# Contador de servicios
total_services=0
compliant_count=0
non_compliant_count=0

# Análisis por servicio
for endpoint in $HEALTH_ENDPOINTS; do
    if [[ -z "$endpoint" ]] || [[ "$endpoint" == "null" ]]; then
        continue
    fi

    # Extraer nombre del servicio del endpoint
    service_name=$(echo "$endpoint" | sed 's|https\?://||' | sed 's|/.*||' | sed 's|\.|_|g')

    if [[ -z "$service_name" ]] || [[ ${#service_name} -lt 3 ]]; then
        continue
    fi

    total_services=$((total_services + 1))

    log_info "Analizando: $service_name ($endpoint)"

    # 1. Disponibilidad
    availability_query="avg_over_time(probe_success{instance=\"$endpoint\"}[$PERIOD])"
    availability=$(prometheus_query "$availability_query")

    # 2. Tiempo de respuesta P95
    response_time_query="quantile_over_time(0.95, probe_duration_seconds{instance=\"$endpoint\"}[$PERIOD])"
    response_time=$(prometheus_query "$response_time_query")

    # 3. Tasa de errores (usar probe_http_status_code)
    error_rate_query="(sum(rate(probe_http_status_code{instance=\"$endpoint\",code=~\"5..\"}[$PERIOD])) or vector(0)) / sum(rate(probe_http_status_code{instance=\"$endpoint\"}[$PERIOD]))"
    error_rate=$(prometheus_query "$error_rate_query")

    # Si no hay datos, establecer valores por defecto
    if [[ "$availability" == "0" ]] || [[ "$availability" == "" ]]; then
        availability="0"
    fi

    if [[ "$response_time" == "0" ]] || [[ "$response_time" == "" ]]; then
        response_time="999"  # Valor alto para indicar problema
    fi

    if [[ "$error_rate" == "0" ]] || [[ "$error_rate" == "" ]]; then
        error_rate="0"
    fi

    # Calcular compliance score
    compliance_score=$(calculate_compliance_score "$availability" "$response_time" "$error_rate")

    # Almacenar datos
    services_data["$service_name,availability"]=$availability
    services_data["$service_name,response_time"]=$response_time
    services_data["$service_name,error_rate"]=$error_rate
    services_data["$service_name,endpoint"]=$endpoint
    service_scores["$service_name"]=$compliance_score

    # Determinar compliance
    is_compliant=true

    if (( $(echo "$availability < $SIX_SIGMA_AVAILABILITY" | bc -l) )); then
        is_compliant=false
    fi

    if (( $(echo "$response_time > $SIX_SIGMA_RESPONSE_TIME" | bc -l) )); then
        is_compliant=false
    fi

    if (( $(echo "$error_rate > $SIX_SIGMA_ERROR_RATE" | bc -l) )); then
        is_compliant=false
    fi

    if $is_compliant; then
        compliant_services+=("$service_name")
        compliant_count=$((compliant_count + 1))
    else
        non_compliant_services+=("$service_name")
        non_compliant_count=$((non_compliant_count + 1))
    fi
done

# Calcular métricas generales
if [[ $total_services -gt 0 ]]; then
    compliance_percentage=$(echo "scale=2; $compliant_count * 100 / $total_services" | bc -l)
else
    compliance_percentage="0"
fi

# Mostrar resultados según formato
case "$FORMAT" in
    "json")
        # Formato JSON
        echo "{"
        echo "  \"analysis\": {"
        echo "    \"timestamp\": \"$ANALYSIS_TIME\","
        echo "    \"period\": \"$PERIOD\","
        echo "    \"total_services\": $total_services,"
        echo "    \"compliant_services\": $compliant_count,"
        echo "    \"non_compliant_services\": $non_compliant_count,"
        echo "    \"compliance_percentage\": $compliance_percentage"
        echo "  },"
        echo "  \"standards\": {"
        echo "    \"availability_threshold\": $SIX_SIGMA_AVAILABILITY,"
        echo "    \"response_time_threshold\": $SIX_SIGMA_RESPONSE_TIME,"
        echo "    \"error_rate_threshold\": $SIX_SIGMA_ERROR_RATE"
        echo "  },"
        echo "  \"services\": ["

        first=true
        for service in "${!service_scores[@]}"; do
            if ! $first; then echo ","; fi
            first=false

            availability=${services_data["$service,availability"]}
            response_time=${services_data["$service,response_time"]}
            error_rate=${services_data["$service,error_rate"]}
            endpoint=${services_data["$service,endpoint"]}
            score=${service_scores["$service"]}

            avail_pct=$(echo "scale=6; $availability * 100" | bc -l)

            echo "    {"
            echo "      \"service\": \"$service\","
            echo "      \"endpoint\": \"$endpoint\","
            echo "      \"availability_percent\": $avail_pct,"
            echo "      \"response_time_seconds\": $response_time,"
            echo "      \"error_rate_percent\": $(echo "scale=6; $error_rate * 100" | bc -l),"
            echo "      \"compliance_score\": $score,"
            echo "      \"six_sigma_compliant\": $(if (( $(echo "$score >= 95" | bc -l) )); then echo "true"; else echo "false"; fi)"
            echo -n "    }"
        done
        echo ""
        echo "  ]"
        echo "}"
        ;;

    "summary")
        # Formato resumen ejecutivo
        echo ""
        log_header "📋 RESUMEN EJECUTIVO SIX SIGMA"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo -e "${BLUE}📅 Período de análisis:${NC} $PERIOD"
        echo -e "${BLUE}🕒 Timestamp:${NC} $ANALYSIS_TIME"
        echo ""

        # Métricas generales
        echo -e "${PURPLE}📊 MÉTRICAS GENERALES:${NC}"
        echo "  • Total de servicios analizados: $total_services"
        echo "  • Servicios conformes: $compliant_count"
        echo "  • Servicios no conformes: $non_compliant_count"
        echo "  • Porcentaje de compliance: $compliance_percentage%"
        echo ""

        if [[ $compliant_count -eq $total_services ]]; then
            log_success "🏆 TODOS LOS SERVICIOS CUMPLEN ESTÁNDARES SIX SIGMA"
        elif [[ $compliance_percentage > 90 ]]; then
            log_warning "⚠️  LA MAYORÍA DE SERVICIOS CUMPLEN ESTÁNDARES ($compliance_percentage%)"
        else
            log_error "🚨 MÚLTIPLES SERVICIOS NO CUMPLEN ESTÁNDARES SIX SIGMA"
        fi

        echo ""

        # Top 3 mejores servicios
        if [[ ${#service_scores[@]} -gt 0 ]]; then
            echo -e "${GREEN}🏆 TOP SERVICIOS (por score):${NC}"
            for service in $(for k in "${!service_scores[@]}"; do echo "${service_scores[$k]} $k"; done | sort -rn | head -3 | cut -d' ' -f2); do
                score=${service_scores["$service"]}
                endpoint=${services_data["$service,endpoint"]}
                echo "  • $service: $(printf "%.1f" $score)% - $endpoint"
            done
            echo ""
        fi

        # Servicios que requieren atención
        if [[ ${#non_compliant_services[@]} -gt 0 ]]; then
            echo -e "${RED}🚨 REQUIEREN ATENCIÓN INMEDIATA:${NC}"
            for service in "${non_compliant_services[@]}"; do
                availability=${services_data["$service,availability"]}
                response_time=${services_data["$service,response_time"]}
                avail_pct=$(echo "scale=4; $availability * 100" | bc -l)
                echo "  • $service: $avail_pct% disponibilidad, ${response_time}s respuesta"
            done
        fi
        ;;

    *)
        # Formato tabla (default)
        echo ""
        log_header "📊 RESULTADOS DE COMPLIANCE SIX SIGMA"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        printf "%-25s %-12s %-12s %-12s %-8s %-10s\n" "SERVICIO" "DISPONIB.%" "RESPUESTA(s)" "ERRORES%" "SCORE" "COMPLIANCE"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        # Mostrar datos de cada servicio
        for service in $(printf '%s\n' "${!service_scores[@]}" | sort); do
            availability=${services_data["$service,availability"]}
            response_time=${services_data["$service,response_time"]}
            error_rate=${services_data["$service,error_rate"]}
            score=${service_scores["$service"]}

            # Formatear valores
            avail_pct=$(printf "%.4f" $(echo "$availability * 100" | bc -l))
            resp_time_fmt=$(printf "%.3f" $response_time)
            error_pct=$(printf "%.6f" $(echo "$error_rate * 100" | bc -l))
            score_fmt=$(printf "%.1f" $score)

            # Determinar status de compliance
            if (( $(echo "$score >= 95" | bc -l) )); then
                compliance_status="✅ PASS"
                color="$GREEN"
            else
                compliance_status="❌ FAIL"
                color="$RED"
            fi

            # Truncar nombre del servicio si es muy largo
            service_short=$(echo "$service" | cut -c1-24)

            printf "${color}%-25s %-12s %-12s %-12s %-8s %-10s${NC}\n" \
                "$service_short" "$avail_pct" "$resp_time_fmt" "$error_pct" "$score_fmt" "$compliance_status"
        done

        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        echo ""
        echo -e "${PURPLE}📊 RESUMEN:${NC}"
        echo "  • Total de servicios: $total_services"
        echo "  • Servicios Six Sigma conformes: $compliant_count"
        echo "  • Servicios no conformes: $non_compliant_count"
        echo "  • Porcentaje de compliance: $compliance_percentage%"

        echo ""
        echo -e "${BLUE}🎯 ESTÁNDARES SIX SIGMA:${NC}"
        echo "  • Disponibilidad: >= $(printf "%.5f" $(echo "$SIX_SIGMA_AVAILABILITY * 100" | bc -l))%"
        echo "  • Tiempo de respuesta P95: <= ${SIX_SIGMA_RESPONSE_TIME}s"
        echo "  • Tasa de errores: <= $(printf "%.5f" $(echo "$SIX_SIGMA_ERROR_RATE * 100" | bc -l))%"
        ;;
esac

echo ""
echo -e "${BLUE}🌐 ACCESO AL SISTEMA:${NC}"
echo "  📊 Dashboard: $GRAFANA_URL/d/entersys-3s/"
echo "  📈 Prometheus: $PROMETHEUS_URL"
echo ""

# Status final
echo ""
if [[ $compliance_percentage == "100.00" ]]; then
    echo -e "${GREEN}🏆 ¡EXCELENTE! TODOS LOS SERVICIOS CUMPLEN SIX SIGMA${NC}"
elif (( $(echo "$compliance_percentage >= 90" | bc -l) )); then
    echo -e "${YELLOW}⚠️  BUEN NIVEL DE COMPLIANCE, REVISAR SERVICIOS CRÍTICOS${NC}"
else
    echo -e "${RED}🚨 ATENCIÓN REQUERIDA: MÚLTIPLES SERVICIOS NO CUMPLEN SLA${NC}"
fi

echo ""
log_info "Análisis completado en $(date -u +"%Y-%m-%d %H:%M:%S UTC")"