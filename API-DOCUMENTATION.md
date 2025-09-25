# 📋 Entersys.mx API Documentation

## 🌐 Base URL
```
https://api.dev.entersys.mx
```

## 🔐 Authentication
Most endpoints require API key authentication via header:
```
X-API-Key: your-api-key-here
```

---

## 📊 Health & Status Endpoints

### GET /api/v1/health
**Description:** Basic API health check
**Authentication:** None required
**Response:**
```json
{
  "status": "ok",
  "database_connection": "ok"
}
```

---

## 🗂️ Smartsheet Middleware API

### Overview
RESTful middleware for Smartsheet API integration with advanced filtering, pagination, and monitoring capabilities.

### Authentication
All Smartsheet endpoints require:
```
X-API-Key: smartsheet_production_api_key_2025_secure
```

---

### GET /api/v1/smartsheet/health
**Description:** Smartsheet service health check
**Authentication:** Required (X-API-Key)

**Response:**
```json
{
  "status": "healthy",
  "user": "armandocortes@entersys.mx",
  "api_base_url": "https://api.smartsheet.com/2.0",
  "timestamp": "2025-09-24T18:30:00.000Z"
}
```

---

### GET /api/v1/smartsheet/sheets/{sheet_id}/rows
**Description:** Get rows from a Smartsheet with advanced filtering and pagination
**Authentication:** Required (X-API-Key)

**Path Parameters:**
- `sheet_id` (integer, required): Smartsheet ID

**Query Parameters:**
- `limit` (integer, optional, 1-1000, default: 100): Maximum rows to return
- `offset` (integer, optional, ≥0, default: 0): Pagination offset
- `fields` (string, optional): Comma-separated column names to include
- `includeAttachments` (boolean, optional, default: false): Include attachment metadata
- `q` (string, optional): Dynamic filter query

**Dynamic Filtering (`q` parameter):**

**Syntax:** `[column_name]:[operator]:[value]`
**Multiple conditions:** `condition1,LOGIC_OP,condition2`

**Supported Operators:**
- `equals`: Exact match (case sensitive)
- `iequals`: Exact match (case insensitive)
- `contains`: Contains text
- `icontains`: Contains text (case insensitive)
- `not_equals`: Not equal to
- `is_empty`: Cell is empty
- `not_empty`: Cell is not empty
- `greater_than`: Greater than (numbers/dates)
- `less_than`: Less than (numbers/dates)

**Logical Operators:** `AND`, `OR`

**Examples:**
```bash
# Basic query
GET /api/v1/smartsheet/sheets/1837320408878980/rows?limit=10

# With filtering
GET /api/v1/smartsheet/sheets/1837320408878980/rows?q=Cliente:equals:AWALAB

# Complex filtering
GET /api/v1/smartsheet/sheets/1837320408878980/rows?q=Status:equals:Active,AND,Priority:not_equals:Low

# Field selection with attachments
GET /api/v1/smartsheet/sheets/1837320408878980/rows?fields=ID,Cliente,ERP&includeAttachments=true

# Pagination with filtering
GET /api/v1/smartsheet/sheets/1837320408878980/rows?q=Cliente:icontains:lab&limit=25&offset=50
```

**Response:**
```json
{
  "success": true,
  "data": {
    "sheet_id": 1837320408878980,
    "total_rows": 250,
    "returned_rows": 50,
    "offset": 0,
    "limit": 50,
    "rows": [
      {
        "id": 987654321,
        "row_number": 1,
        "cells": {
          "ID": "1",
          "Cliente": "AWALAB",
          "ERP": "Bind",
          "API URL": "https://api.bind.com.mx/v1/invoices"
        },
        "attachments": [],
        "created_at": "2025-09-17T22:12:03Z",
        "modified_at": "2025-09-17T22:12:03Z",
        "created_by": null,
        "modified_by": null
      }
    ]
  },
  "filters_applied": "Cliente:equals:AWALAB",
  "execution_time_ms": 1250
}
```

---

### GET /api/v1/smartsheet/sheets/{sheet_id}/columns
**Description:** Get column information from a Smartsheet
**Authentication:** Required (X-API-Key)

**Path Parameters:**
- `sheet_id` (integer, required): Smartsheet ID

**Response:**
```json
[
  {
    "id": 5047396274491268,
    "index": 0,
    "title": "ID",
    "type": "TEXT_NUMBER",
    "primary": false,
    "hidden": false,
    "locked": false
  },
  {
    "id": 2795596460806020,
    "index": 1,
    "title": "Cliente",
    "type": "TEXT_NUMBER",
    "primary": true,
    "hidden": false,
    "locked": false
  }
]
```

---

## 🚨 Error Responses

### Common Error Formats

**400 Bad Request:**
```json
{
  "detail": "Invalid query syntax: Operator must be one of: equals, contains, ..."
}
```

**401 Unauthorized:**
```json
{
  "detail": "Invalid API key"
}
```

**404 Not Found:**
```json
{
  "detail": "Sheet with ID 123456 not found"
}
```

**502 Bad Gateway:**
```json
{
  "detail": "Smartsheet service error: API connection failed"
}
```

**Smartsheet Error Response:**
```json
{
  "success": false,
  "error": "SMARTSHEET_API_ERROR",
  "error_code": "1006",
  "message": "Smartsheet API error: Sheet not found",
  "timestamp": "2025-09-24T18:30:00.000Z"
}
```

---

## 📈 Performance & Monitoring

### Response Times
- **Typical response time:** 1.1-1.3 seconds
- **Includes execution_time_ms** in all successful responses

### Rate Limits
- Respects Smartsheet API rate limits
- Stateless design supports multiple concurrent requests

### Monitoring Integration
- **Structured JSON logs** with rotation
- **Prometheus metrics** available:
  - `api_requests_total{method,endpoint,status}`
  - `api_request_duration_seconds{method,endpoint}`
  - `smartsheet_operations_total{operation,status}`
  - `smartsheet_active_connections`

### Log Files
- `logs/app.log` - General application logs
- `logs/errors.log` - Error-only logs
- `logs/smartsheet.log` - Smartsheet-specific operations
- `logs/api.log` - HTTP request logs

---

## 🔧 Development & Testing

### Interactive Documentation
```
https://api.dev.entersys.mx/docs
```

### Test Sheet ID
For testing and development:
```
Sheet ID: 1837320408878980
```

### Sample cURL Commands

**Health Check:**
```bash
curl -H "X-API-Key: smartsheet_production_api_key_2025_secure" \
     https://api.dev.entersys.mx/api/v1/smartsheet/health
```

**Get Sheet Data:**
```bash
curl -H "X-API-Key: smartsheet_production_api_key_2025_secure" \
     "https://api.dev.entersys.mx/api/v1/smartsheet/sheets/1837320408878980/rows?limit=5"
```

**Filter by Client:**
```bash
curl -H "X-API-Key: smartsheet_production_api_key_2025_secure" \
     "https://api.dev.entersys.mx/api/v1/smartsheet/sheets/1837320408878980/rows?q=Cliente:equals:AWALAB"
```

**Select Specific Fields:**
```bash
curl -H "X-API-Key: smartsheet_production_api_key_2025_secure" \
     "https://api.dev.entersys.mx/api/v1/smartsheet/sheets/1837320408878980/rows?fields=ID,Cliente,ERP&limit=3"
```

---

## 🏗️ Architecture

### Technology Stack
- **Python 3.11+** with FastAPI framework
- **Smartsheet Python SDK 3.0.3** for official API integration
- **Pydantic** for data validation and serialization
- **Structured logging** with JSON format for monitoring
- **Prometheus client** for metrics collection

### Deployment
- **Docker containerized** application
- **Traefik** reverse proxy with SSL termination
- **PostgreSQL** database for core application data
- **Google Cloud Platform** infrastructure

---

## 📞 Support

For API support or issues:
1. Check logs: `docker logs entersys-content-api`
2. View Smartsheet logs: `docker exec entersys-content-api tail -f logs/smartsheet.log`
3. Monitor metrics via Grafana dashboard
4. Review this documentation for proper usage

---

**Last Updated:** September 24, 2025
**API Version:** 1.0
**Smartsheet Middleware Version:** 1.0