"""
CORTEX v5.0 — Dashboard Router.
"""

import base64
import hashlib
import hmac
import io
import json
import os
import secrets
import time
import zipfile
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine_async import AsyncCortexEngine
from cortex.swarm.actuators.skill import (
    SkillActuator,
    build_canonical_kpi_snapshot,
    extract_canonical_kpi_snapshot_record,
    extract_canonical_metrics,
)
from cortex.swarm.discovery import SkillMetadata, SkillRegistry

__all__ = ["router", "get_dashboard_html"]

_DASHBOARD_TOKEN_TTL_SECONDS = 900
_DASHBOARD_EXPORT_SCOPE = "__dashboard_export__"
_DASHBOARD_ACTION_SECRET = (
    os.environ.get("CORTEX_DASHBOARD_ACTION_SECRET")
    or os.environ.get("CORTEX_GATE_SECRET")
    or os.environ.get("CORTEX_VAULT_KEY")
    or secrets.token_hex(32)
)


class DashboardSnapshotRequest(BaseModel):
    """Manual dashboard snapshot action request."""

    token: str


def get_dashboard_html(
    initial_kpis: list[dict[str, Any]] | None = None,
    *,
    xlsx_export_token: str | None = None,
) -> str:
    """Return the HTML payload for the dashboard."""
    boot_payload = json.dumps(initial_kpis or []).replace("</", "<\\/")
    export_token = json.dumps(xlsx_export_token or "")
    return (
        r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>CORTEX Dashboard</title>
        <style>
            :root {
                color-scheme: dark;
                --bg: #07111f;
                --panel: rgba(11, 26, 46, 0.88);
                --panel-border: rgba(120, 199, 255, 0.22);
                --text: #ecf7ff;
                --muted: #8eb4cc;
                --accent: #66f0c9;
                --accent-2: #7dc3ff;
                --danger: #ff7c8c;
            }
            * { box-sizing: border-box; }
            body {
                margin: 0;
                min-height: 100vh;
                font-family: "Iosevka Term", "SFMono-Regular", "Menlo", monospace;
                background:
                    radial-gradient(circle at top left, rgba(102, 240, 201, 0.16), transparent 28%),
                    radial-gradient(circle at top right, rgba(125, 195, 255, 0.18), transparent 30%),
                    linear-gradient(180deg, #091425 0%, #050a12 100%);
                color: var(--text);
            }
            .shell {
                max-width: 1200px;
                margin: 0 auto;
                padding: 32px 20px 48px;
            }
            .hero {
                display: flex;
                justify-content: space-between;
                gap: 24px;
                align-items: flex-end;
                margin-bottom: 28px;
            }
            .hero h1 {
                margin: 0;
                font-size: clamp(2rem, 4vw, 3.4rem);
                letter-spacing: -0.04em;
            }
            .hero p {
                margin: 8px 0 0;
                color: var(--muted);
                max-width: 720px;
                line-height: 1.5;
            }
            .status-chip {
                border: 1px solid var(--panel-border);
                background: rgba(102, 240, 201, 0.1);
                color: var(--accent);
                padding: 10px 14px;
                border-radius: 999px;
                white-space: nowrap;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 16px;
            }
            .panel {
                border: 1px solid var(--panel-border);
                background: var(--panel);
                backdrop-filter: blur(16px);
                border-radius: 18px;
                padding: 18px;
                box-shadow: 0 18px 48px rgba(0, 0, 0, 0.22);
            }
            .panel h2 {
                margin: 0 0 12px;
                font-size: 1rem;
                color: var(--accent-2);
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }
            .panel-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 16px;
                margin-bottom: 12px;
            }
            .panel-header h2 {
                margin: 0;
            }
            .panel-actions {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .history-window-group {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 4px;
                border: 1px solid var(--panel-border);
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.03);
            }
            .history-window-button {
                border: 0;
                background: transparent;
                color: var(--muted);
                padding: 6px 10px;
                border-radius: 999px;
                font: inherit;
                cursor: pointer;
            }
            .history-window-button.is-active {
                background: rgba(102, 240, 201, 0.12);
                color: var(--text);
            }
            .kpi-card {
                display: grid;
                gap: 10px;
                min-height: 150px;
            }
            .kpi-trend {
                height: 56px;
                width: 100%;
                display: block;
            }
            .kpi-trend polyline {
                fill: none;
                stroke: var(--accent);
                stroke-width: 2.5;
                stroke-linecap: round;
                stroke-linejoin: round;
            }
            .kpi-trend .kpi-trend-baseline {
                stroke: rgba(125, 195, 255, 0.18);
                stroke-width: 1;
            }
            .kpi-footnote {
                display: flex;
                justify-content: space-between;
                gap: 12px;
                color: var(--muted);
                font-size: 0.8rem;
            }
            .kpi-actions {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
                margin-top: 4px;
            }
            .kpi-button {
                border: 1px solid var(--panel-border);
                background: rgba(102, 240, 201, 0.08);
                color: var(--text);
                padding: 8px 12px;
                border-radius: 999px;
                font: inherit;
                cursor: pointer;
                transition: transform 120ms ease, background 120ms ease;
            }
            .kpi-button:hover {
                background: rgba(102, 240, 201, 0.16);
                transform: translateY(-1px);
            }
            .kpi-button[disabled] {
                cursor: wait;
                opacity: 0.72;
                transform: none;
            }
            .kpi-status {
                min-height: 1.2rem;
                color: var(--muted);
                font-size: 0.8rem;
                text-align: right;
            }
            .kpi-status.error {
                color: var(--danger);
            }
            .global-status {
                min-height: 1.2rem;
                color: var(--muted);
                font-size: 0.82rem;
                text-align: right;
            }
            .global-status.error {
                color: var(--danger);
            }
            .kpi-name {
                color: var(--muted);
                font-size: 0.9rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }
            .kpi-value {
                font-size: clamp(1.8rem, 4vw, 2.8rem);
                font-weight: 700;
                color: var(--text);
                line-height: 1;
            }
            .kpi-delta {
                display: inline-flex;
                align-items: center;
                width: fit-content;
                max-width: 100%;
                padding: 4px 8px;
                border-radius: 999px;
                font-size: 0.8rem;
                line-height: 1.2;
                border: 1px solid var(--panel-border);
                background: rgba(255, 255, 255, 0.03);
            }
            .kpi-delta.positive {
                color: var(--accent);
                background: rgba(102, 240, 201, 0.08);
            }
            .kpi-delta.negative {
                color: var(--danger);
                background: rgba(255, 124, 140, 0.08);
            }
            .kpi-delta.neutral {
                color: var(--muted);
            }
            .kpi-meta {
                color: var(--muted);
                font-size: 0.92rem;
                line-height: 1.5;
            }
            .empty-state, .error-state {
                padding: 18px;
                border-radius: 16px;
                border: 1px dashed var(--panel-border);
                color: var(--muted);
                background: rgba(255, 255, 255, 0.02);
            }
            .error-state { color: var(--danger); }
        </style>
        <script>
            function sanitize(str) {
                if (!str) return '';
                return String(str).replace(/[&<>"']/g, function(m) {
                    return '&#' + m.charCodeAt(0) + ';';
                });
            }
            function renderFact(item) {
                return '<div class="fact">' +
                       '<div>Project: ' + sanitize(item.project) + '</div>' +
                       '<div>Type: ' + sanitize(item.fact_type) + '</div>' +
                       '<div>Content: ' + sanitize(item.content) + '</div>' +
                       '<div>Tags: ' + (item.tags ? item.tags.map(function(t) { return sanitize(t); }).join(', ') : '') + '</div></div>';
            }
            function formatMetricValue(value) {
                if (typeof value === 'number') {
                    return value.toLocaleString('en-US');
                }
                return sanitize(value);
            }
            function computeDeltaSummary(history, metricName) {
                if (!history || history.length < 2) {
                    return { label: 'No prior snapshot', className: 'neutral' };
                }
                var values = history
                    .map(function(entry) { return entry.metrics ? entry.metrics[metricName] : null; })
                    .filter(function(value) { return typeof value === 'number'; });
                if (values.length < 2) {
                    return { label: 'No prior snapshot', className: 'neutral' };
                }
                var current = values[values.length - 1];
                var previous = values[values.length - 2];
                var delta = current - previous;
                if (delta === 0) {
                    return { label: 'Δ 0 vs prev', className: 'neutral' };
                }
                var direction = delta > 0 ? 'positive' : 'negative';
                var sign = delta > 0 ? '+' : '−';
                var absolute = Math.abs(delta).toLocaleString('en-US');
                return { label: 'Δ ' + sign + absolute + ' vs prev', className: direction };
            }
            function renderKpiCard(item) {
                var metrics = item.metrics || {};
                var metricNames = Object.keys(metrics);
                var headline = metricNames[0] || 'Metric';
                var history = item.history || [];
                var visibleHistory = getVisibleHistory(history);
                var sparkline = renderSparkline(visibleHistory, headline);
                var delta = computeDeltaSummary(visibleHistory, headline);
                var secondary = metricNames.slice(1).map(function(name) {
                    return '<div>' + sanitize(name) + ': ' + formatMetricValue(metrics[name]) + '</div>';
                }).join('');
                var historyCount = history.length;
                var latestSnapshot = historyCount ? sanitize(history[historyCount - 1].captured_at) : 'live only';
                var historyWindowLabel = historyCount ? ('window: last ' + Math.min(selectedHistoryWindow, historyCount)) : 'window: 0';
                var status = window.__CORTEX_KPI_STATUS__[item.skill_name];
                var statusClass = status && status.error ? 'kpi-status error' : 'kpi-status';
                var statusText = status ? sanitize(status.message) : '';
                var disabledAttr = status && status.pending ? ' disabled' : '';
                return (
                    '<section class="panel kpi-card">' +
                        '<div class="kpi-name">' + sanitize(item.skill_name) + '</div>' +
                        '<div class="kpi-value">' + formatMetricValue(metrics[headline]) + '</div>' +
                        '<div class="kpi-meta">' + sanitize(headline) + '</div>' +
                        '<div class="kpi-delta ' + sanitize(delta.className) + '">' + sanitize(delta.label) + '</div>' +
                        sparkline +
                        '<div class="kpi-meta">' + secondary + '</div>' +
                        '<div class="kpi-actions">' +
                            '<button class="kpi-button" data-snapshot-skill="' + sanitize(item.skill_name) + '"' + disabledAttr + '>' +
                                'Capture Snapshot' +
                            '</button>' +
                            '<div class="' + statusClass + '">' + statusText + '</div>' +
                        '</div>' +
                        '<div class="kpi-footnote">' +
                            '<span>snapshots: ' + historyCount + ' · ' + sanitize(historyWindowLabel) + '</span>' +
                            '<span>latest: ' + latestSnapshot + '</span>' +
                        '</div>' +
                    '</section>'
                );
            }
            function renderSparkline(history, metricName) {
                if (!history.length) {
                    return '<div class="kpi-meta">No persisted history yet.</div>';
                }
                var values = history
                    .map(function(entry) { return entry.metrics ? entry.metrics[metricName] : null; })
                    .filter(function(value) { return typeof value === 'number'; });
                if (!values.length) {
                    return '<div class="kpi-meta">History available without numeric trend.</div>';
                }
                var min = Math.min.apply(null, values);
                var max = Math.max.apply(null, values);
                var span = Math.max(max - min, 1);
                var width = 220;
                var height = 56;
                var step = values.length > 1 ? width / (values.length - 1) : 0;
                var points = values.map(function(value, index) {
                    var x = index * step;
                    var y = height - (((value - min) / span) * (height - 8)) - 4;
                    return x.toFixed(2) + ',' + y.toFixed(2);
                }).join(' ');
                return (
                    '<svg class="kpi-trend" viewBox="0 0 ' + width + ' ' + height + '" preserveAspectRatio="none" aria-label="trend">' +
                        '<line class="kpi-trend-baseline" x1="0" y1="' + (height - 4) + '" x2="' + width + '" y2="' + (height - 4) + '"></line>' +
                        '<polyline points="' + points + '"></polyline>' +
                    '</svg>'
                );
            }
            const initialKpis = __INITIAL_KPIS__;
            const xlsxExportToken = __XLSX_EXPORT_TOKEN__;
            const historyWindowStorageKey = 'cortex.dashboard.historyWindow';
            let kpiState = initialKpis.slice();
            let selectedHistoryWindow = 12;
            window.__CORTEX_KPI_BOOTSTRAP__ = initialKpis;
            window.__CORTEX_KPI_STATUS__ = {};
            function loadPersistedHistoryWindow() {
                try {
                    var raw = window.localStorage.getItem(historyWindowStorageKey);
                    var parsed = Number(raw);
                    if ([3, 7, 12].indexOf(parsed) !== -1) {
                        selectedHistoryWindow = parsed;
                    }
                } catch (error) {
                    selectedHistoryWindow = 12;
                }
            }
            function persistHistoryWindow(windowSize) {
                try {
                    window.localStorage.setItem(historyWindowStorageKey, String(windowSize));
                } catch (error) {
                    return;
                }
            }
            function getVisibleHistory(history) {
                var windowSize = selectedHistoryWindow;
                if (!history || !history.length) {
                    return [];
                }
                if (!windowSize || history.length <= windowSize) {
                    return history.slice();
                }
                return history.slice(history.length - windowSize);
            }
            function setGlobalSnapshotStatus(message, options) {
                var status = document.getElementById('capture-all-status');
                var button = document.getElementById('capture-all-kpis');
                var isError = options && options.error;
                var isPending = options && options.pending;
                if (status) {
                    status.textContent = message || '';
                    status.className = isError ? 'global-status error' : 'global-status';
                }
                if (button) {
                    button.disabled = !!isPending;
                }
            }
            function buildExportPayload() {
                return {
                    exported_at: new Date().toISOString(),
                    history_window: selectedHistoryWindow,
                    skills: kpiState.map(function(item) {
                        var history = item.history || [];
                        return {
                            skill_name: item.skill_name,
                            trigger: item.trigger,
                            metrics: item.metrics,
                            content: item.content,
                            latest_snapshot: item.latest_snapshot || null,
                            history: getVisibleHistory(history)
                        };
                    })
                };
            }
            function escapeCsvValue(value) {
                if (value === null || typeof value === 'undefined') {
                    return '';
                }
                var normalized = String(value);
                if (/[",\n]/.test(normalized)) {
                    return '"' + normalized.replace(/"/g, '""') + '"';
                }
                return normalized;
            }
            function buildCsvExportRows() {
                return kpiState.flatMap(function(item) {
                    var history = item.history || [];
                    var visibleHistory = getVisibleHistory(history);
                    var latestVisible = visibleHistory.length
                        ? visibleHistory[visibleHistory.length - 1]
                        : null;
                    var metricNames = Object.keys(item.metrics || {});
                    var headline = metricNames[0] || 'Metric';
                    var delta = computeDeltaSummary(visibleHistory, headline);
                    return metricNames.map(function(metricName) {
                        return {
                            skill_name: item.skill_name,
                            trigger: item.trigger || '',
                            metric_name: metricName,
                            metric_value: item.metrics[metricName],
                            latest_snapshot: item.latest_snapshot || '',
                            visible_history_points: visibleHistory.length,
                            history_window: selectedHistoryWindow,
                            delta_label: metricName === headline ? delta.label : '',
                            latest_visible_captured_at: latestVisible ? latestVisible.captured_at : '',
                        };
                    });
                });
            }
            function buildCsvExportContent() {
                var rows = buildCsvExportRows();
                var columns = [
                    'skill_name',
                    'trigger',
                    'metric_name',
                    'metric_value',
                    'latest_snapshot',
                    'visible_history_points',
                    'history_window',
                    'delta_label',
                    'latest_visible_captured_at'
                ];
                return [columns.join(',')].concat(
                    rows.map(function(row) {
                        return columns.map(function(column) {
                            return escapeCsvValue(row[column]);
                        }).join(',');
                    })
                ).join('\n');
            }
            async function copyKpiJson() {
                var payload = JSON.stringify(buildExportPayload(), null, 2);
                try {
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        await navigator.clipboard.writeText(payload);
                        setGlobalSnapshotStatus('Visible KPI JSON copied.', {});
                        return;
                    }
                    throw new Error('clipboard unavailable');
                } catch (error) {
                    try {
                        window.prompt('Copy KPI JSON', payload);
                        setGlobalSnapshotStatus('Visible KPI JSON ready to copy.', {});
                    } catch (promptError) {
                        setGlobalSnapshotStatus('Copy failed in this browser.', { error: true });
                    }
                }
            }
            async function copyKpiCsv() {
                if (!kpiState.length) {
                    setGlobalSnapshotStatus('No KPI skills available.', { error: true });
                    return;
                }
                var payload = buildCsvExportContent();
                try {
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        await navigator.clipboard.writeText(payload);
                        setGlobalSnapshotStatus('Visible KPI CSV copied.', {});
                        return;
                    }
                    throw new Error('clipboard unavailable');
                } catch (error) {
                    try {
                        window.prompt('Copy KPI CSV', payload);
                        setGlobalSnapshotStatus('Visible KPI CSV ready to copy.', {});
                    } catch (promptError) {
                        setGlobalSnapshotStatus('CSV copy failed in this browser.', { error: true });
                    }
                }
            }
            function downloadKpiJson() {
                var payload = JSON.stringify(buildExportPayload(), null, 2);
                var filename = 'cortex-kpi-export-' +
                    new Date().toISOString().replace(/[:.]/g, '-') +
                    '.json';
                var anchor = null;
                var objectUrl = null;
                try {
                    if (
                        typeof Blob === 'undefined' ||
                        !window.URL ||
                        typeof window.URL.createObjectURL !== 'function'
                    ) {
                        throw new Error('download unavailable');
                    }
                    var blob = new Blob([payload], { type: 'application/json;charset=utf-8' });
                    objectUrl = window.URL.createObjectURL(blob);
                    anchor = document.createElement('a');
                    anchor.href = objectUrl;
                    anchor.download = filename;
                    anchor.style.display = 'none';
                    document.body.appendChild(anchor);
                    anchor.click();
                    setGlobalSnapshotStatus('Visible KPI JSON downloaded.', {});
                } catch (error) {
                    setGlobalSnapshotStatus('Download failed in this browser.', { error: true });
                } finally {
                    if (anchor && anchor.parentNode) {
                        anchor.parentNode.removeChild(anchor);
                    }
                    if (objectUrl && window.URL && typeof window.URL.revokeObjectURL === 'function') {
                        window.URL.revokeObjectURL(objectUrl);
                    }
                }
            }
            function downloadKpiCsv() {
                if (!kpiState.length) {
                    setGlobalSnapshotStatus('No KPI skills available.', { error: true });
                    return;
                }
                var csv = buildCsvExportContent();
                var filename = 'cortex-kpi-export-' +
                    new Date().toISOString().replace(/[:.]/g, '-') +
                    '.csv';
                var anchor = null;
                var objectUrl = null;
                try {
                    if (
                        typeof Blob === 'undefined' ||
                        !window.URL ||
                        typeof window.URL.createObjectURL !== 'function'
                    ) {
                        throw new Error('download unavailable');
                    }
                    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
                    objectUrl = window.URL.createObjectURL(blob);
                    anchor = document.createElement('a');
                    anchor.href = objectUrl;
                    anchor.download = filename;
                    anchor.style.display = 'none';
                    document.body.appendChild(anchor);
                    anchor.click();
                    setGlobalSnapshotStatus('Visible KPI CSV downloaded.', {});
                } catch (error) {
                    setGlobalSnapshotStatus('CSV download failed in this browser.', { error: true });
                } finally {
                    if (anchor && anchor.parentNode) {
                        anchor.parentNode.removeChild(anchor);
                    }
                    if (objectUrl && window.URL && typeof window.URL.revokeObjectURL === 'function') {
                        window.URL.revokeObjectURL(objectUrl);
                    }
                }
            }
            function downloadKpiXlsx() {
                if (!xlsxExportToken) {
                    setGlobalSnapshotStatus('XLSX export unavailable.', { error: true });
                    return;
                }
                var url = '/dashboard/skills/export.xlsx?token=' +
                    encodeURIComponent(xlsxExportToken) +
                    '&window=' + encodeURIComponent(String(selectedHistoryWindow));
                var anchor = document.createElement('a');
                anchor.href = url;
                anchor.style.display = 'none';
                document.body.appendChild(anchor);
                anchor.click();
                anchor.remove();
                setGlobalSnapshotStatus('Downloading KPI XLSX…', {});
            }
            function renderCanonicalKpis() {
                var mount = document.getElementById('canonical-kpis');
                if (!kpiState.length) {
                    mount.innerHTML = '<div class="empty-state">No canonical KPI skills found.</div>';
                    setGlobalSnapshotStatus('No KPI skills available.', {});
                    return;
                }
                document.querySelectorAll('[data-history-window]').forEach(function(button) {
                    var isActive = Number(button.getAttribute('data-history-window')) === selectedHistoryWindow;
                    button.classList.toggle('is-active', isActive);
                });
                mount.innerHTML = kpiState.map(renderKpiCard).join('');
            }
            async function captureSnapshot(skillName) {
                var item = kpiState.find(function(entry) { return entry.skill_name === skillName; });
                if (!item || !item.snapshot_token) {
                    window.__CORTEX_KPI_STATUS__[skillName] = {
                        message: 'Snapshot token unavailable.',
                        error: true
                    };
                    renderCanonicalKpis();
                    return;
                }

                window.__CORTEX_KPI_STATUS__[skillName] = { message: 'Saving snapshot…', pending: true };
                renderCanonicalKpis();

                try {
                    var response = await fetch('/dashboard/skills/' + encodeURIComponent(skillName) + '/snapshot', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ token: item.snapshot_token })
                    });
                    var payload = await response.json();
                    if (!response.ok) {
                        throw new Error(payload.detail || 'snapshot failed');
                    }
                    kpiState = kpiState.map(function(entry) {
                        return entry.skill_name === skillName ? payload : entry;
                    });
                    window.__CORTEX_KPI_STATUS__[skillName] = {
                        message: 'Snapshot captured at ' + payload.latest_snapshot,
                        pending: false
                    };
                    renderCanonicalKpis();
                } catch (error) {
                    window.__CORTEX_KPI_STATUS__[skillName] = {
                        message: (error && error.message) ? error.message : 'Snapshot failed',
                        error: true
                    };
                    renderCanonicalKpis();
                }
            }
            async function captureAllSnapshots() {
                if (!kpiState.length) {
                    setGlobalSnapshotStatus('No KPI skills available.', { error: true });
                    return;
                }
                setGlobalSnapshotStatus('Capturing all KPI snapshots…', { pending: true });
                var completed = 0;
                try {
                    for (var index = 0; index < kpiState.length; index += 1) {
                        await captureSnapshot(kpiState[index].skill_name);
                        completed += 1;
                    }
                    setGlobalSnapshotStatus('Captured ' + completed + ' KPI snapshots.', {});
                } catch (error) {
                    setGlobalSnapshotStatus(
                        (error && error.message) ? error.message : 'Capture-all failed',
                        { error: true }
                    );
                } finally {
                    var button = document.getElementById('capture-all-kpis');
                    if (button) {
                        button.disabled = false;
                    }
                }
            }
            function setHistoryWindow(windowSize) {
                selectedHistoryWindow = windowSize;
                persistHistoryWindow(windowSize);
                renderCanonicalKpis();
            }
            window.addEventListener('DOMContentLoaded', function() {
                loadPersistedHistoryWindow();
                renderCanonicalKpis();
                setGlobalSnapshotStatus('', {});
                document.getElementById('canonical-kpis').addEventListener('click', function(event) {
                    var button = event.target.closest('[data-snapshot-skill]');
                    if (!button) return;
                    captureSnapshot(button.getAttribute('data-snapshot-skill'));
                });
                document.getElementById('capture-all-kpis').addEventListener('click', function() {
                    captureAllSnapshots();
                });
                document.getElementById('copy-kpi-json').addEventListener('click', function() {
                    copyKpiJson();
                });
                document.getElementById('copy-kpi-csv').addEventListener('click', function() {
                    copyKpiCsv();
                });
                document.getElementById('download-kpi-json').addEventListener('click', function() {
                    downloadKpiJson();
                });
                document.getElementById('download-kpi-csv').addEventListener('click', function() {
                    downloadKpiCsv();
                });
                document.getElementById('download-kpi-xlsx').addEventListener('click', function() {
                    downloadKpiXlsx();
                });
                document.querySelectorAll('[data-history-window]').forEach(function(button) {
                    button.addEventListener('click', function() {
                        setHistoryWindow(Number(button.getAttribute('data-history-window')));
                    });
                });
            });
        </script>
    </head>
    <body>
        <main class="shell">
            <header class="hero">
                <div>
                    <h1>CORTEX Dashboard</h1>
                    <p>Operational memory, swarm signals, and canonical KPI skills in one live surface.</p>
                </div>
                <div class="status-chip">KPI skills live</div>
            </header>
            <section>
                <div class="panel">
                    <div class="panel-header">
                        <h2>Canonical KPIs</h2>
                        <div class="panel-actions">
                            <div class="history-window-group" aria-label="History Window">
                                <button class="history-window-button" data-history-window="3">3</button>
                                <button class="history-window-button" data-history-window="7">7</button>
                                <button class="history-window-button is-active" data-history-window="12">12</button>
                            </div>
                            <button id="copy-kpi-json" class="kpi-button">Copy KPI JSON</button>
                            <button id="copy-kpi-csv" class="kpi-button">Copy KPI CSV</button>
                            <button id="download-kpi-json" class="kpi-button">Download KPI JSON</button>
                            <button id="download-kpi-csv" class="kpi-button">Download KPI CSV</button>
                            <button id="download-kpi-xlsx" class="kpi-button">Download KPI XLSX</button>
                            <button id="capture-all-kpis" class="kpi-button">Capture All Snapshots</button>
                            <div id="capture-all-status" class="global-status"></div>
                        </div>
                    </div>
                    <div id="canonical-kpis" class="grid">
                        <div class="empty-state">Loading canonical KPI skills...</div>
                    </div>
                </div>
            </section>
            <section style="margin-top: 18px;">
                <div id="app"></div>
            </section>
        </main>
    </body>
    </html>
    """
    ).replace("__INITIAL_KPIS__", boot_payload).replace("__XLSX_EXPORT_TOKEN__", export_token)


def _coerce_history_window(window: int) -> int:
    if window not in {3, 7, 12}:
        raise HTTPException(status_code=400, detail="Unsupported history window")
    return window


def _window_history(history: list[dict[str, Any]], window: int) -> list[dict[str, Any]]:
    if len(history) <= window:
        return list(history)
    return history[-window:]


def _delta_label(history: list[dict[str, Any]], metric_name: str) -> str:
    values = [
        value
        for entry in history
        if isinstance((value := (entry.get("metrics") or {}).get(metric_name)), (int, float))
        and not isinstance(value, bool)
    ]
    if len(values) < 2:
        return "No prior snapshot"
    delta = values[-1] - values[-2]
    if delta == 0:
        return "Δ 0 vs prev"
    sign = "+" if delta > 0 else "−"
    return f"Δ {sign}{abs(delta):,} vs prev"


def _numeric_metric_values(history: list[dict[str, Any]], metric_name: str) -> list[float]:
    values: list[float] = []
    for entry in history:
        value = (entry.get("metrics") or {}).get(metric_name)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(float(value))
    return values


def _delta_percent_label(history: list[dict[str, Any]], metric_name: str) -> str:
    values = _numeric_metric_values(history, metric_name)
    if len(values) < 2:
        return ""
    previous = values[-2]
    current = values[-1]
    if previous == 0:
        if current == 0:
            return "0.0%"
        return "n/a"
    delta_percent = ((current - previous) / abs(previous)) * 100
    return f"{delta_percent:.1f}%"


def _trend_status(history: list[dict[str, Any]], metric_name: str) -> str:
    values = _numeric_metric_values(history, metric_name)
    if len(values) < 2:
        return "live_only"
    delta = values[-1] - values[-2]
    if delta > 0:
        return "positive"
    if delta < 0:
        return "negative"
    return "neutral"


def _build_dashboard_executive_rows(
    payloads: list[dict[str, Any]],
    *,
    history_window: int,
) -> list[list[Any]]:
    rows: list[list[Any]] = [
        [
            "skill_name",
            "trigger",
            "primary_metric",
            "current_value",
            "previous_value",
            "delta_value",
            "delta_percent",
            "trend_status",
            "latest_snapshot",
            "visible_history_points",
            "history_window",
            "window_start",
            "window_end",
        ]
    ]
    for payload in payloads:
        visible_history = _window_history(payload.get("history") or [], history_window)
        metrics = payload.get("metrics") or {}
        metric_names = list(metrics.keys())
        primary_metric = metric_names[0] if metric_names else "Metric"
        metric_values = _numeric_metric_values(visible_history, primary_metric)
        current_value = metrics.get(primary_metric, "")
        numeric_previous = metric_values[-2] if len(metric_values) >= 2 else None
        previous_value = numeric_previous if numeric_previous is not None else ""
        delta_value = ""
        if isinstance(current_value, (int, float)) and numeric_previous is not None:
            delta_value = current_value - numeric_previous
        rows.append(
            [
                payload.get("skill_name", ""),
                payload.get("trigger", ""),
                primary_metric,
                current_value,
                previous_value,
                delta_value,
                _delta_percent_label(visible_history, primary_metric),
                _trend_status(visible_history, primary_metric),
                payload.get("latest_snapshot") or "",
                len(visible_history),
                history_window,
                visible_history[0]["captured_at"] if visible_history else "",
                visible_history[-1]["captured_at"] if visible_history else "",
            ]
        )
    return rows


def _build_dashboard_summary_rows(
    payloads: list[dict[str, Any]],
    *,
    history_window: int,
) -> list[list[Any]]:
    rows: list[list[Any]] = [
        [
            "skill_name",
            "trigger",
            "metric_name",
            "metric_value",
            "latest_snapshot",
            "visible_history_points",
            "history_window",
            "delta_label",
            "latest_visible_captured_at",
        ]
    ]
    for payload in payloads:
        visible_history = _window_history(payload.get("history") or [], history_window)
        latest_visible = visible_history[-1]["captured_at"] if visible_history else ""
        metrics = payload.get("metrics") or {}
        metric_names = list(metrics.keys())
        headline = metric_names[0] if metric_names else "Metric"
        for metric_name in metric_names:
            rows.append(
                [
                    payload.get("skill_name", ""),
                    payload.get("trigger", ""),
                    metric_name,
                    metrics.get(metric_name, ""),
                    payload.get("latest_snapshot") or "",
                    len(visible_history),
                    history_window,
                    _delta_label(visible_history, headline) if metric_name == headline else "",
                    latest_visible,
                ]
            )
    return rows


def _build_dashboard_history_rows(
    payloads: list[dict[str, Any]],
    *,
    history_window: int,
) -> list[list[Any]]:
    rows: list[list[Any]] = [
        ["skill_name", "captured_at", "metric_name", "metric_value", "history_window"]
    ]
    for payload in payloads:
        visible_history = _window_history(payload.get("history") or [], history_window)
        for record in visible_history:
            metrics = record.get("metrics") or {}
            for metric_name, metric_value in metrics.items():
                rows.append(
                    [
                        payload.get("skill_name", ""),
                        record.get("captured_at", ""),
                        metric_name,
                        metric_value,
                        history_window,
                    ]
                )
    return rows


def _xlsx_column_name(index: int) -> str:
    column = ""
    value = index + 1
    while value:
        value, remainder = divmod(value - 1, 26)
        column = chr(65 + remainder) + column
    return column


def _xlsx_cell_xml(row_index: int, column_index: int, value: Any, *, header: bool) -> str:
    reference = f"{_xlsx_column_name(column_index)}{row_index}"
    style = ' s="1"' if header else ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{reference}"{style}><v>{value}</v></c>'
    text = xml_escape("" if value is None else str(value))
    return (
        f'<c r="{reference}" t="inlineStr"{style}>'
        f'<is><t xml:space="preserve">{text}</t></is>'
        f"</c>"
    )


def _build_sheet_xml(rows: list[list[Any]]) -> str:
    sheet_rows: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells = "".join(
            _xlsx_cell_xml(row_index, column_index, value, header=row_index == 1)
            for column_index, value in enumerate(row)
        )
        sheet_rows.append(f'<row r="{row_index}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        + "".join(sheet_rows)
        + "</sheetData></worksheet>"
    )


def _build_xlsx_workbook(sheets: list[tuple[str, list[list[Any]]]]) -> bytes:
    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        (
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        ),
        (
            '<Override PartName="/xl/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        ),
    ]
    for index in range(len(sheets)):
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{index + 1}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    content_types.append("</Types>")

    workbook_xml = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        (
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
        ),
    ]
    workbook_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for index, (sheet_name, _) in enumerate(sheets, start=1):
        workbook_xml.append(
            f'<sheet name="{xml_escape(sheet_name)}" sheetId="{index}" r:id="rId{index}"/>'
        )
        workbook_rels.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    style_rel_id = len(sheets) + 1
    workbook_xml.append("</sheets></workbook>")
    workbook_rels.append(
        f'<Relationship Id="rId{style_rel_id}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    workbook_rels.append("</Relationships>")

    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2">'
        '<font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font>'
        "</fonts>"
        '<fills count="2"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
        "</cellXfs>"
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )

    package_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    workbook = io.BytesIO()
    with zipfile.ZipFile(workbook, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "".join(content_types))
        archive.writestr("_rels/.rels", package_rels)
        archive.writestr("xl/workbook.xml", "".join(workbook_xml))
        archive.writestr("xl/_rels/workbook.xml.rels", "".join(workbook_rels))
        archive.writestr("xl/styles.xml", styles_xml)
        for index, (_, rows) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _build_sheet_xml(rows))
    return workbook.getvalue()


def _dashboard_token_signature(payload_json: str) -> str:
    return hmac.new(
        _DASHBOARD_ACTION_SECRET.encode("utf-8"),
        payload_json.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def issue_dashboard_action_token(
    *,
    tenant_id: str,
    skill_name: str,
    project: str = "metrics",
    ttl_seconds: int = _DASHBOARD_TOKEN_TTL_SECONDS,
) -> str:
    """Issue a short-lived HMAC token for dashboard actions."""
    payload = {
        "exp": int(time.time()) + ttl_seconds,
        "project": project,
        "skill_name": skill_name,
        "tenant_id": tenant_id,
    }
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload_bytes = base64.urlsafe_b64encode(payload_json.encode("utf-8")).rstrip(b"=")
    return f"{payload_bytes.decode('ascii')}.{_dashboard_token_signature(payload_json)}"


def verify_dashboard_action_token(
    token: str,
    *,
    skill_name: str,
) -> dict[str, Any]:
    """Verify and decode a short-lived dashboard action token."""
    try:
        encoded_payload, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Invalid dashboard action token") from exc

    padding = "=" * (-len(encoded_payload) % 4)
    try:
        payload_json = base64.urlsafe_b64decode(f"{encoded_payload}{padding}").decode("utf-8")
        payload = json.loads(payload_json)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=403, detail="Invalid dashboard action token") from exc

    expected_signature = _dashboard_token_signature(payload_json)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=403, detail="Invalid dashboard action token")
    if payload.get("skill_name") != skill_name:
        raise HTTPException(status_code=403, detail="Dashboard action token scope mismatch")

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at < int(time.time()):
        raise HTTPException(status_code=410, detail="Dashboard action token expired")

    tenant_id = payload.get("tenant_id")
    project = payload.get("project")
    if not isinstance(tenant_id, str) or not tenant_id:
        raise HTTPException(status_code=403, detail="Invalid dashboard action token")
    if not isinstance(project, str) or not project:
        raise HTTPException(status_code=403, detail="Invalid dashboard action token")

    return payload


def _resolve_metrics_skills(registry: SkillRegistry) -> list[SkillMetadata]:
    return sorted(
        (
            skill
            for skill in registry.skills.values()
            if skill.category == "metrics" and extract_canonical_metrics(skill)
        ),
        key=lambda skill: skill.name,
    )


async def _build_dashboard_skill_payload(
    *,
    skill: SkillMetadata,
    tenant_id: str,
    fact_history: list[dict[str, Any]],
    project: str,
    history_limit: int,
) -> dict[str, Any]:
    response = await SkillActuator(skill).execute("report canonical kpi", {})
    history = [
        record
        for fact in fact_history
        if (record := extract_canonical_kpi_snapshot_record(fact, skill.name)) is not None
    ]
    ordered_history = sorted(
        history,
        key=lambda record: (record["captured_at"], record["created_at"], record["fact_id"]),
    )[-history_limit:]
    return {
        "skill_name": response["metadata"]["skill_name"],
        "trigger": response["metadata"]["trigger"],
        "metrics": response["metadata"]["metrics"],
        "content": response["content"],
        "history": ordered_history,
        "latest_snapshot": ordered_history[-1]["captured_at"] if ordered_history else None,
        "snapshot_token": issue_dashboard_action_token(
            tenant_id=tenant_id,
            skill_name=skill.name,
            project=project,
        ),
    }


async def _load_canonical_kpis(
    engine: AsyncCortexEngine,
    tenant_id: str,
    *,
    project: str = "metrics",
    history_limit: int = 12,
) -> list[dict[str, Any]]:
    """Resolve canonical KPI payloads plus persisted history for dashboard bootstrap."""
    registry = SkillRegistry()
    registry.scan()
    skills = _resolve_metrics_skills(registry)
    fact_history = await engine.history(project=project, tenant_id=tenant_id)

    payloads: list[dict[str, Any]] = []
    for skill in skills:
        payloads.append(
            await _build_dashboard_skill_payload(
                skill=skill,
                tenant_id=tenant_id,
                fact_history=fact_history,
                project=project,
                history_limit=history_limit,
            )
        )
    return payloads


router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> str:
    """Serve the embedded memory dashboard."""
    from cortex.routes.dashboard import get_dashboard_html

    return get_dashboard_html(
        await _load_canonical_kpis(engine, auth.tenant_id),
        xlsx_export_token=issue_dashboard_action_token(
            tenant_id=auth.tenant_id,
            skill_name=_DASHBOARD_EXPORT_SCOPE,
        ),
    )


@router.get("/dashboard/skills/export.xlsx")
async def download_dashboard_kpi_xlsx(
    token: str,
    window: int = 12,
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> Response:
    """Export the dashboard KPI panel as an XLSX workbook."""
    token_payload = verify_dashboard_action_token(token, skill_name=_DASHBOARD_EXPORT_SCOPE)
    tenant_id = token_payload["tenant_id"]
    project = token_payload["project"]
    history_window = _coerce_history_window(window)
    payloads = await _load_canonical_kpis(
        engine,
        tenant_id,
        project=project,
        history_limit=12,
    )
    workbook = _build_xlsx_workbook(
        [
            ("Executive View", _build_dashboard_executive_rows(payloads, history_window=history_window)),
            ("KPI Summary", _build_dashboard_summary_rows(payloads, history_window=history_window)),
            ("KPI History", _build_dashboard_history_rows(payloads, history_window=history_window)),
        ]
    )
    filename = f"cortex-kpi-export-{int(time.time())}.xlsx"
    return Response(
        content=workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/dashboard/skills/{skill_name}/snapshot")
async def capture_dashboard_skill_snapshot(
    skill_name: str,
    request: DashboardSnapshotRequest,
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict[str, Any]:
    """Persist a manual KPI snapshot from the dashboard using a signed short-lived token."""
    token_payload = verify_dashboard_action_token(request.token, skill_name=skill_name)
    tenant_id = token_payload["tenant_id"]
    project = token_payload["project"]

    registry = SkillRegistry()
    registry.scan()
    skill = next((item for item in _resolve_metrics_skills(registry) if item.name == skill_name), None)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Unknown KPI skill: {skill_name}")

    snapshot = build_canonical_kpi_snapshot(skill)
    fact_id = await engine.store(
        project=project,
        content=snapshot["content"],
        tenant_id=tenant_id,
        fact_type="knowledge",
        tags=["kpi", "skill", skill.name, "dashboard"],
        source="dashboard:skills",
        meta={
            "skill_name": skill.name,
            "trigger": skill.trigger,
            "captured_at": snapshot["captured_at"],
            "metrics": snapshot["metrics"],
            "snapshot_origin": "dashboard",
        },
    )

    fact_history = await engine.history(project=project, tenant_id=tenant_id)
    payload = await _build_dashboard_skill_payload(
        skill=skill,
        tenant_id=tenant_id,
        fact_history=fact_history,
        project=project,
        history_limit=12,
    )
    payload["fact_id"] = fact_id
    return payload
