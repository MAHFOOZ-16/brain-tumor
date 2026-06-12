from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import psycopg2
from psycopg2.extras import DictCursor
import uuid
from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st
from PIL import Image


APP_VERSION = "2026.04.29-pro4"

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "exp.pt"
DATA_DIR = BASE_DIR / "patient_data"
DB_PATH = DATA_DIR / "brain_tumor_app.db"
UPLOAD_DIR = DATA_DIR / "uploads"
PREDICTION_DIR = DATA_DIR / "predictions"
EXPORT_DIR = DATA_DIR / "exports"
DOCTOR_DATA_DIR = DATA_DIR / "doctors"
LEGACY_RECORDS_FILE = DATA_DIR / "records.json"
CACHE_DIR = DATA_DIR / ".cache"
MPLCONFIG_DIR = DATA_DIR / ".matplotlib"
DEFAULT_DOCTOR_EMAIL = "doctor@example.com"
DEFAULT_DOCTOR_PASSWORD = "braincare123"

os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIG_DIR))


def page_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #06080d;
            --panel: rgba(15, 19, 28, 0.82);
            --panel-strong: rgba(22, 27, 38, 0.94);
            --panel-soft: rgba(255, 255, 255, 0.055);
            --text: #f5f7fb;
            --muted: #9ba7b7;
            --line: rgba(255, 255, 255, 0.12);
            --teal: #24d2a4;
            --cyan: #58c7ff;
            --coral: #ff6b5f;
            --amber: #ffbf5b;
            --green: #7ddf64;
            --shadow: 0 24px 80px rgba(0, 0, 0, 0.36);
        }

        html {
            background: var(--bg);
        }

        .stApp {
            background:
                linear-gradient(115deg, rgba(36, 210, 164, 0.08), transparent 32%),
                linear-gradient(245deg, rgba(255, 107, 95, 0.07), transparent 28%),
                linear-gradient(180deg, #05070c 0%, #0a1018 48%, #07090f 100%);
            color: var(--text);
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            opacity: 0.34;
            background-image:
                linear-gradient(rgba(255,255,255,0.055) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px);
            background-size: 64px 64px;
            mask-image: linear-gradient(to bottom, black, transparent 82%);
        }

        .stApp::after {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background: linear-gradient(180deg, transparent, rgba(36, 210, 164, 0.10), transparent);
            transform: translateY(-100%);
            animation: scanline 9s linear infinite;
            opacity: 0.24;
        }

        .neural-bg {
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            overflow: hidden;
            opacity: 0.78;
        }

        .neural-bg svg {
            width: 100%;
            height: 100%;
            min-width: 760px;
            transform-origin: center;
            animation: neural-drift 34s ease-in-out infinite alternate;
        }

        .neural-bg path {
            stroke: var(--cyan);
            stroke-width: 1.25;
            stroke-linecap: round;
            stroke-dasharray: 8 20;
            opacity: 0.22;
            animation: neural-flow 18s linear infinite;
        }

        .neural-bg path:nth-child(2n) {
            stroke: var(--teal);
            animation-duration: 24s;
            animation-direction: reverse;
        }

        @keyframes scanline {
            0% { transform: translateY(-100%); }
            100% { transform: translateY(100%); }
        }

        @keyframes neural-flow {
            to { stroke-dashoffset: -220; }
        }

        @keyframes neural-drift {
            from { transform: translate3d(-1.5%, -1%, 0) scale(1.03); }
            to { transform: translate3d(1.5%, 1%, 0) scale(1.08); }
        }

        @keyframes rise {
            from { opacity: 0; transform: translateY(14px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes auth-panel-in {
            from { opacity: 0; transform: translateX(18px); filter: blur(4px); }
            to { opacity: 1; transform: translateX(0); filter: blur(0); }
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        #MainMenu,
        footer {
            display: none !important;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        section.main {
            margin-left: 0 !important;
            padding-left: 0 !important;
            width: 100vw !important;
            max-width: 100vw !important;
        }

        .main .block-container {
            max-width: 1320px;
            padding: 1.15rem 1.45rem 4rem;
            position: relative;
            z-index: 2;
        }

        [data-testid="stHorizontalBlock"] {
            min-width: 0 !important;
        }

        [data-testid="column"] {
            min-width: 0 !important;
        }

        h1, h2, h3, h4, p, label, span, div {
            letter-spacing: 0;
        }

        h1 {
            color: var(--text);
            font-size: clamp(2.1rem, 4vw, 4.6rem);
            line-height: 0.98;
            font-weight: 760;
            margin: 0;
        }

        h2 {
            color: var(--text);
            font-size: 1.45rem;
            font-weight: 720;
            margin-top: 0;
        }

        h3 {
            color: var(--text);
            font-size: 1.05rem;
            font-weight: 680;
        }

        p, label, .stMarkdown, .stTextInput label, .stTextArea label,
        .stNumberInput label, .stSelectbox label, .stSlider label, .stFileUploader label {
            color: var(--text) !important;
        }

        .muted {
            color: var(--muted);
        }

        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            padding: 0.9rem 1rem;
            margin-bottom: 1rem;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: rgba(8, 11, 17, 0.72);
            box-shadow: var(--shadow);
            backdrop-filter: blur(18px);
            animation: rise 0.45s ease-out both;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }

        .brand-mark {
            width: 42px;
            height: 42px;
            border-radius: 8px;
            display: grid;
            place-items: center;
            font-weight: 760;
            color: #06110d;
            background: linear-gradient(135deg, var(--teal), var(--amber));
            box-shadow: 0 0 34px rgba(36, 210, 164, 0.25);
        }

        .brand-title {
            font-size: 1.05rem;
            font-weight: 760;
            color: var(--text);
        }

        .brand-subtitle {
            color: var(--muted);
            font-size: 0.83rem;
            margin-top: 0.08rem;
        }

        .doctor-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.55rem;
            color: var(--text);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.62rem 0.78rem;
            background: rgba(255, 255, 255, 0.055);
            white-space: nowrap;
        }

        .top-actions {
            display: flex;
            gap: 0.7rem;
            align-items: center;
            justify-content: flex-end;
        }

        .theme-note {
            color: var(--muted);
            font-size: 0.78rem;
            text-align: right;
            margin-top: -0.2rem;
        }

        .auth-wrap {
            min-height: calc(100vh - 4rem);
            max-width: 1180px;
            margin: 0 auto;
            padding-top: clamp(2rem, 9vh, 7rem);
            animation: rise 0.55s ease-out both;
        }

        .auth-copy {
            padding: 1rem 0 0.5rem;
            text-align: left;
        }

        .eyebrow {
            color: var(--teal);
            font-size: 0.78rem;
            font-weight: 760;
            text-transform: uppercase;
            margin-bottom: 0.9rem;
        }

        .hero-copy {
            color: #cad2df;
            font-size: 1.02rem;
            line-height: 1.7;
            max-width: 640px;
            margin-top: 1.1rem;
            margin-left: 0;
            margin-right: 0;
        }

        .auth-card,
        .surface,
        .metric-card,
        .patient-banner,
        .report-card,
        .vault-card,
        [data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--panel);
            box-shadow: var(--shadow);
            backdrop-filter: blur(18px);
            animation: rise 0.5s ease-out both;
        }

        .auth-card {
            padding: 1.25rem;
            max-width: 520px;
            margin: 1.3rem auto 0;
            background:
                linear-gradient(180deg, rgba(255, 255, 255, 0.10), rgba(255, 255, 255, 0.035)),
                var(--panel-strong);
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            max-width: 540px;
            margin: 1.3rem auto 0;
            background:
                linear-gradient(180deg, rgba(255, 255, 255, 0.10), rgba(255, 255, 255, 0.035)),
                var(--panel-strong) !important;
            animation: auth-panel-in 0.38s cubic-bezier(0.2, 0.8, 0.2, 1) both;
        }

        .surface {
            padding: 1.05rem;
            margin-bottom: 1rem;
        }

        .section-title {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: end;
            margin: 1.4rem 0 0.7rem;
        }

        .section-kicker {
            color: var(--muted);
            font-size: 0.9rem;
            margin-top: 0.18rem;
        }

        .hero-panel {
            overflow: hidden;
            position: relative;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: clamp(1.2rem, 3vw, 2rem);
            min-height: 255px;
            background:
                linear-gradient(120deg, rgba(11, 16, 25, 0.96), rgba(13, 23, 33, 0.84)),
                repeating-linear-gradient(90deg, rgba(36, 210, 164, 0.16) 0 1px, transparent 1px 18px);
            box-shadow: var(--shadow);
            animation: rise 0.5s ease-out both;
        }

        .hero-panel::after {
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            bottom: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--teal), var(--amber), var(--coral), var(--cyan));
        }

        .hero-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.7rem;
            margin-top: 1.3rem;
            justify-content: flex-start;
        }

        .pill {
            display: inline-flex;
            align-items: center;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.48rem 0.62rem;
            color: #dfe6ef;
            background: rgba(255, 255, 255, 0.06);
            font-size: 0.86rem;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
            margin: 1rem 0;
        }

        .metric-card {
            padding: 1rem;
            min-height: 116px;
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.82rem;
            margin-bottom: 0.5rem;
        }

        .metric-value {
            color: var(--text);
            font-size: 1.85rem;
            font-weight: 760;
            line-height: 1.05;
        }

        .metric-note {
            color: var(--muted);
            font-size: 0.78rem;
            margin-top: 0.55rem;
        }

        .patient-banner {
            padding: 1.1rem;
            margin: 0.75rem 0 1rem;
            background:
                linear-gradient(135deg, rgba(36, 210, 164, 0.12), rgba(255, 191, 91, 0.05)),
                var(--panel);
        }

        .patient-name {
            color: var(--text);
            font-weight: 760;
            font-size: 1.35rem;
        }

        .patient-meta {
            color: var(--muted);
            font-size: 0.92rem;
            margin-top: 0.26rem;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            border-radius: 8px;
            padding: 0.38rem 0.56rem;
            font-size: 0.8rem;
            font-weight: 720;
            border: 1px solid rgba(255, 255, 255, 0.16);
            background: rgba(255, 255, 255, 0.06);
        }

        .status-positive {
            color: #ffb4ad;
            background: rgba(255, 107, 95, 0.14);
            border-color: rgba(255, 107, 95, 0.35);
        }

        .status-negative {
            color: #acf09c;
            background: rgba(125, 223, 100, 0.13);
            border-color: rgba(125, 223, 100, 0.32);
        }

        .status-review {
            color: #ffe0a8;
            background: rgba(255, 191, 91, 0.14);
            border-color: rgba(255, 191, 91, 0.34);
        }

        .report-card {
            padding: 1.1rem;
            background:
                linear-gradient(145deg, rgba(36, 210, 164, 0.11), rgba(88, 199, 255, 0.05)),
                var(--panel);
        }

        .report-title {
            color: var(--text);
            font-size: 1.05rem;
            font-weight: 760;
            margin-bottom: 0.55rem;
        }

        .report-body {
            color: #d6f8ef;
            line-height: 1.65;
        }

        .vault-card {
            padding: 1rem;
            margin-bottom: 0.75rem;
        }

        .vault-preview {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.05);
            margin-top: 0.8rem;
        }

        .vault-label {
            color: var(--muted);
            font-size: 0.8rem;
            margin-bottom: 0.28rem;
        }

        .vault-path {
            color: #eef5fb;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 0.87rem;
            word-break: break-word;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stSelectbox [data-baseweb="select"],
        .stFileUploader section,
        .stSlider [data-baseweb="slider"] {
            border-radius: 8px !important;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input {
            color: var(--text) !important;
            background: rgba(255, 255, 255, 0.075) !important;
            border: 1px solid var(--line) !important;
        }

        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stNumberInput input:focus {
            border-color: rgba(36, 210, 164, 0.62) !important;
            box-shadow: 0 0 0 2px rgba(36, 210, 164, 0.12) !important;
        }

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button {
            border-radius: 8px !important;
            min-height: 2.75rem;
            font-weight: 720;
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
            color: var(--text) !important;
            background: rgba(255, 255, 255, 0.075) !important;
            transition: transform 0.16s ease, border-color 0.16s ease, background 0.16s ease;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {
            transform: translateY(-1px);
            border-color: rgba(36, 210, 164, 0.60) !important;
            background: rgba(36, 210, 164, 0.12) !important;
        }

        .stButton > button[kind="primary"],
        [data-testid="stFormSubmitButton"] > button[kind="primary"] {
            color: #04110d !important;
            background: linear-gradient(135deg, var(--teal), var(--amber)) !important;
            border-color: transparent !important;
        }

        div[role="radiogroup"] {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            padding: 0.25rem;
            margin: 0.2rem 0 1.1rem;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.045);
        }

        div[role="radiogroup"] label {
            border-radius: 8px;
            padding: 0.55rem 0.75rem;
            color: var(--muted) !important;
        }

        div[role="radiogroup"] label:has(input:checked) {
            background: rgba(36, 210, 164, 0.18);
            color: var(--text) !important;
            box-shadow: inset 0 0 0 1px rgba(36, 210, 164, 0.35), 0 0 30px rgba(36, 210, 164, 0.08);
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
        }

        .stImage img {
            border-radius: 8px;
            border: 1px solid var(--line);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.30);
        }

        .stAlert {
            border-radius: 8px;
        }

        [data-testid="InputInstructions"] {
            display: none !important;
        }

        hr {
            border-color: var(--line);
        }

        @media (max-width: 980px) {
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
            }

            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
            }

            .metric-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .topbar {
                align-items: flex-start;
                flex-direction: column;
            }

            .doctor-chip {
                white-space: normal;
            }

            .auth-wrap {
                padding-top: 1.4rem;
            }

            .auth-copy {
                text-align: center;
            }

            .hero-copy {
                margin-left: auto;
                margin-right: auto;
            }

            .hero-meta {
                justify-content: center;
            }
        }

        @media (max-width: 640px) {
            .main .block-container {
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }

            h1 {
                font-size: 2.05rem;
            }

            .hero-copy {
                font-size: 0.95rem;
            }

            .pill {
                width: 100%;
                justify-content: center;
            }

            div[role="radiogroup"] {
                display: grid;
                grid-template-columns: 1fr;
            }

            .metric-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.session_state.get("light_mode", False):
        st.markdown(
            """
            <style>
            :root {
                --bg: #f5f8fb;
                --panel: rgba(255, 255, 255, 0.82);
                --panel-strong: rgba(255, 255, 255, 0.96);
                --panel-soft: rgba(20, 33, 61, 0.055);
                --text: #111827;
                --muted: #566275;
                --line: rgba(17, 24, 39, 0.14);
                --shadow: 0 24px 80px rgba(31, 41, 55, 0.13);
            }

            .stApp {
                background:
                    linear-gradient(115deg, rgba(36, 210, 164, 0.16), transparent 34%),
                    linear-gradient(245deg, rgba(88, 199, 255, 0.18), transparent 30%),
                    linear-gradient(180deg, #f7fbfc 0%, #eef7f6 58%, #f8fafc 100%);
            }

            .stApp::before {
                opacity: 0.20;
                background-image:
                    linear-gradient(rgba(18, 70, 84, 0.13) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(18, 70, 84, 0.10) 1px, transparent 1px);
            }

            .stApp::after {
                background: linear-gradient(180deg, transparent, rgba(36, 210, 164, 0.14), transparent);
                opacity: 0.18;
            }

            .topbar,
            .hero-panel,
            .metric-card,
            .patient-banner,
            .report-card,
            .vault-card,
            [data-testid="stVerticalBlockBorderWrapper"] {
                background:
                    linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(255, 255, 255, 0.58)),
                    var(--panel) !important;
                border-color: rgba(15, 23, 42, 0.13) !important;
                box-shadow: 0 24px 80px rgba(15, 23, 42, 0.11) !important;
            }

            .topbar {
                background: rgba(255, 255, 255, 0.70) !important;
            }

            .hero-panel {
                background:
                    linear-gradient(120deg, rgba(255, 255, 255, 0.80), rgba(236, 249, 248, 0.70)),
                    repeating-linear-gradient(90deg, rgba(36, 210, 164, 0.14) 0 1px, transparent 1px 18px) !important;
            }

            .hero-panel::before {
                background: linear-gradient(90deg, transparent, rgba(88, 199, 255, 0.22), transparent);
                opacity: 0.85;
            }

            .brand-title,
            .patient-name,
            .metric-value,
            .report-title {
                color: #111827;
            }

            .brand-subtitle,
            .patient-meta,
            .metric-label,
            .metric-note,
            .section-kicker {
                color: #5a6678;
            }

            .hero-copy {
                color: #425167;
            }

            .report-body {
                color: #1c493c;
            }

            .pill,
            .doctor-chip,
            .vault-path {
                color: #172033;
                background: rgba(255, 255, 255, 0.62);
                border-color: rgba(15, 23, 42, 0.12);
            }

            .stTextInput input,
            .stTextArea textarea,
            .stNumberInput input,
            .stSelectbox div[data-baseweb="select"] {
                color: #111827 !important;
                background: rgba(255, 255, 255, 0.82) !important;
                border-color: rgba(15, 23, 42, 0.18) !important;
            }

            .stSelectbox div[data-baseweb="select"] span {
                color: #111827 !important;
            }

            .stTextInput input::placeholder,
            .stTextArea textarea::placeholder {
                color: #6b7280 !important;
            }

            .stButton > button,
            .stDownloadButton > button,
            [data-testid="stFormSubmitButton"] > button {
                color: #111827 !important;
                background: rgba(255, 255, 255, 0.68) !important;
                border-color: rgba(15, 23, 42, 0.16) !important;
            }

            .stButton > button:hover,
            .stDownloadButton > button:hover,
            [data-testid="stFormSubmitButton"] > button:hover {
                background: rgba(36, 210, 164, 0.16) !important;
                border-color: rgba(36, 210, 164, 0.42) !important;
            }

            .stButton > button[kind="primary"],
            [data-testid="stFormSubmitButton"] > button[kind="primary"] {
                color: #04110d !important;
                background: linear-gradient(135deg, var(--teal), var(--amber)) !important;
                border-color: transparent !important;
            }

            div[role="radiogroup"] {
                background: rgba(255, 255, 255, 0.56) !important;
                border-color: rgba(15, 23, 42, 0.13) !important;
            }

            div[role="radiogroup"] label {
                color: #3e4a5d !important;
            }

            div[role="radiogroup"] label:has(input:checked) {
                color: #0f172a !important;
                background: rgba(36, 210, 164, 0.18);
            }

            .neural-bg {
                opacity: 0.45;
            }

            .neural-bg path {
                stroke: #516f7e;
                opacity: 0.18;
            }

            .neural-bg path:nth-child(2n) {
                stroke: #2b9e86;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )


def render_neural_background() -> None:
    st.markdown(
        """
        <div class="neural-bg" aria-hidden="true">
            <svg viewBox="0 0 1440 980" preserveAspectRatio="xMidYMid slice">
                <path d="M-20 210 C 160 120, 260 310, 430 210 S 780 80, 1020 210 S 1240 360, 1480 210" />
                <path d="M-20 480 C 170 580, 320 380, 520 480 S 880 650, 1080 500 S 1280 350, 1480 470" />
                <path d="M80 -40 C 160 160, 120 350, 280 480 S 360 760, 520 1020" />
                <path d="M560 -40 C 470 210, 680 350, 610 520 S 780 810, 700 1020" />
                <path d="M980 -40 C 1120 160, 940 330, 1120 520 S 1260 750, 1180 1020" />
                <path d="M-20 760 C 210 680, 420 820, 640 720 S 980 570, 1480 820" />
            </svg>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ensure_storage() -> None:
    for path in (DATA_DIR, DOCTOR_DATA_DIR, UPLOAD_DIR, PREDICTION_DIR, EXPORT_DIR, CACHE_DIR, MPLCONFIG_DIR):
        path.mkdir(exist_ok=True)



@st.cache_resource(show_spinner=False)
def get_db_pool(host, port, dbname, user, password, sslmode, connect_timeout):
    from psycopg2.pool import ThreadedConnectionPool
    from psycopg2.extras import DictCursor
    return ThreadedConnectionPool(
        minconn=1,
        maxconn=20,
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        sslmode=sslmode,
        connect_timeout=connect_timeout,
        cursor_factory=DictCursor,
    )


class PgConnection:
    def __init__(self, pool):
        self.pool = pool
        self.conn = pool.getconn()
        if self.conn.closed:
            try:
                pool.putconn(self.conn, close=True)
            except Exception:
                pass
            self.conn = pool.getconn()
        self.conn.autocommit = True
        
    @staticmethod
    def _convert_query(query):
        """Convert SQLite ? placeholders to PostgreSQL %s without breaking existing % or %s."""
        # If the query already contains %s placeholders, assume it's already PostgreSQL-ready
        if '%s' in query:
            return query
        # Otherwise convert ? to %s and escape any literal % (e.g. in LIKE patterns)
        return query.replace('%', '%%').replace('?', '%s')

    def execute(self, query, params=()):
        query = self._convert_query(query)
        from psycopg2.extras import DictCursor
        cur = self.conn.cursor(cursor_factory=DictCursor)
        cur.execute(query, params)
        return cur
        
    def executescript(self, script):
        script = script.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        script = script.replace("INSERT OR IGNORE", "INSERT")
        from psycopg2.extras import DictCursor
        cur = self.conn.cursor(cursor_factory=DictCursor)
        # psycopg2 does not support multiple statements in a single execute() call,
        # so split on ';' and run each statement individually.
        for statement in script.split(";"):
            stmt = statement.strip()
            if stmt:
                cur.execute(stmt)

    def close(self):
        if self.conn and self.pool:
            try:
                self.pool.putconn(self.conn)
            except Exception:
                pass
            self.conn = None

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_connection():
    """Get a connection from the global pool to Supabase PostgreSQL."""
    from urllib.parse import urlparse, unquote
    ensure_storage()
    import streamlit as st

    # Try to read the pooler URL from Streamlit secrets
    try:
        raw_url = st.secrets["database"]["url"]
        p = urlparse(raw_url.strip())
        pool = get_db_pool(
            host=p.hostname,
            port=p.port or 6543,
            dbname=(p.path or "/postgres").lstrip("/") or "postgres",
            user=unquote(p.username or ""),
            password=unquote(p.password or ""),
            sslmode="require",
            connect_timeout=10,
        )
        return PgConnection(pool)
    except Exception:
        pass

    # Fallback: use the known pooler credentials directly
    pool = get_db_pool(
        host="aws-1-eu-north-1.pooler.supabase.com",
        port=6543,
        dbname="postgres",
        user="postgres.fluafavdyhciipfahtuv",
        password="BRAINTUMOR@123",
        sslmode="require",
        connect_timeout=10,
    )
    return PgConnection(pool)



def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                hospital TEXT,
                specialty TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                doctor_id INTEGER NOT NULL,
                mrn TEXT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                sex TEXT NOT NULL,
                phone TEXT,
                risk_level TEXT,
                clinical_notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS scans (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                doctor_id INTEGER NOT NULL,
                modality TEXT NOT NULL,
                original_filename TEXT,
                original_path TEXT NOT NULL,
                prediction_path TEXT,
                top_label TEXT,
                confidence REAL,
                status TEXT,
                summary_headline TEXT,
                summary_details TEXT,
                detections_json TEXT,
                confidence_threshold REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
                FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
            );
            """
        )


def reset_session_on_upgrade() -> None:
    if st.session_state.get("app_version") == APP_VERSION:
        return
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.app_version = APP_VERSION


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def readable_time(value: str | None) -> str:
    if not value:
        return "Not available"
    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y, %H:%M")
    except ValueError:
        return value


def as_dict(row) -> dict | None:
    return dict(row) if row is not None else None


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "profile"


def table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s",
        (table_name,),
    ).fetchone()
    return row is not None


def normalized_identity(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def legacy_patient_matches_doctor(patient: dict, doctor: dict) -> bool:
    email = normalized_identity(doctor.get("email"))
    if email == DEFAULT_DOCTOR_EMAIL:
        return True

    patient_name = normalized_identity(patient["name"])
    patient_mrn = normalized_identity(patient["mrn"])
    doctor_name = normalized_identity(doctor.get("name"))
    hospital = normalized_identity(doctor.get("hospital"))
    email_prefix = normalized_identity((doctor.get("email") or "").split("@", 1)[0])

    return any(
        (
            bool(hospital and patient_mrn and patient_mrn == hospital),
            bool(doctor_name and patient_name and patient_name == doctor_name),
            bool(email_prefix and patient_name and patient_name == email_prefix),
        )
    )


def doctor_workspace_paths(doctor_id: int) -> dict[str, Path]:
    doctor = get_doctor(doctor_id)
    email = doctor.get("email", f"doctor_{doctor_id}") if doctor else f"doctor_{doctor_id}"
    root = DOCTOR_DATA_DIR / f"{doctor_id}_{safe_slug(email)}"
    return {
        "root": root,
        "db": root / "workspace.db",
        "uploads": root / "uploads",
        "predictions": root / "predictions",
        "exports": root / "exports",
        "migration_flag": root / ".migrated_from_shared_db",
    }


def ensure_doctor_workspace(doctor_id: int) -> dict[str, Path]:
    paths = doctor_workspace_paths(doctor_id)
    for key in ("root", "uploads", "predictions", "exports"):
        paths[key].mkdir(parents=True, exist_ok=True)
    return paths


def init_workspace_schema(conn: PgConnection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS patients (
            id TEXT PRIMARY KEY,
            doctor_id INTEGER NOT NULL,
            mrn TEXT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            sex TEXT NOT NULL,
            phone TEXT,
            risk_level TEXT,
            clinical_notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scans (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            doctor_id INTEGER NOT NULL,
            modality TEXT NOT NULL,
            original_filename TEXT,
            original_path TEXT NOT NULL,
            prediction_path TEXT,
            top_label TEXT,
            confidence REAL,
            status TEXT,
            summary_headline TEXT,
            summary_details TEXT,
            detections_json TEXT,
            confidence_threshold REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        );
        """
    )


def get_workspace_connection(doctor_id: int):
    # For Postgres, just return the main connection instead of local file DBs
    return get_connection()


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        220_000,
    ).hex()
    return salt, digest


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    _, digest = hash_password(password, salt)
    return secrets.compare_digest(digest, expected_hash)


def doctor_count() -> int:
    with get_connection() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0])


def create_doctor(name: str, email: str, password: str, hospital: str, specialty: str) -> tuple[bool, str, dict | None]:
    salt, digest = hash_password(password)
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO doctors (name, email, password_hash, salt, hospital, specialty, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (name.strip(), email.strip().lower(), digest, salt, hospital.strip(), specialty.strip(), now_iso()),
            )
            doctor_id = cursor.fetchone()[0]
            doctor = as_dict(conn.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)).fetchone())
            return True, "Account created.", doctor
    except psycopg2.IntegrityError:
        return False, "An account already exists for this email.", None


def ensure_demo_doctor() -> None:
    salt, digest = hash_password(DEFAULT_DOCTOR_PASSWORD)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM doctors WHERE lower(email) = lower(?)",
            (DEFAULT_DOCTOR_EMAIL,),
        ).fetchone()
        if row:
            conn.execute(
                """
                UPDATE doctors
                SET password_hash = ?, salt = ?, name = COALESCE(NULLIF(name, ''), ?),
                    hospital = COALESCE(NULLIF(hospital, ''), ?),
                    specialty = COALESCE(NULLIF(specialty, ''), ?)
                WHERE id = ?
                """,
                (digest, salt, "Demo Doctor", "NeuroDesk Demo Hospital", "Radiology", row["id"]),
            )
            return

        conn.execute(
            """
            INSERT INTO doctors (name, email, password_hash, salt, hospital, specialty, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Demo Doctor",
                DEFAULT_DOCTOR_EMAIL,
                digest,
                salt,
                "NeuroDesk Demo Hospital",
                "Radiology",
                now_iso(),
            ),
        )


def authenticate_doctor(email: str, password: str) -> tuple[bool, str, dict | None]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM doctors WHERE lower(email) = lower(?)",
            (email.strip(),),
        ).fetchone()
    if row is None:
        return False, "No doctor account found for this email.", None

    doctor = dict(row)
    if not verify_password(password, doctor["salt"], doctor["password_hash"]):
        return False, "Incorrect password.", None
    return True, "Signed in.", doctor


def get_doctor(doctor_id: int | None) -> dict | None:
    if doctor_id is None:
        return None
    with get_connection() as conn:
        return as_dict(conn.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)).fetchone())


def new_patient_id() -> str:
    return f"P-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"


def new_scan_id() -> str:
    return f"S-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned or "scan.jpg"


def create_patient(
    doctor_id: int,
    name: str,
    age: int,
    sex: str,
    mrn: str,
    phone: str,
    risk_level: str,
    clinical_notes: str,
) -> str:
    patient_id = new_patient_id()
    with get_workspace_connection(doctor_id) as conn:
        conn.execute(
            """
            INSERT INTO patients (
                id, doctor_id, mrn, name, age, sex, phone, risk_level,
                clinical_notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                doctor_id,
                mrn.strip(),
                name.strip(),
                int(age),
                sex,
                phone.strip(),
                risk_level,
                clinical_notes.strip(),
                now_iso(),
                now_iso(),
            ),
        )
    return patient_id


def update_patient(
    doctor_id: int,
    patient_id: str,
    name: str,
    age: int,
    sex: str,
    mrn: str,
    phone: str,
    risk_level: str,
    clinical_notes: str,
) -> None:
    with get_workspace_connection(doctor_id) as conn:
        conn.execute(
            """
            UPDATE patients
            SET name = ?, age = ?, sex = ?, mrn = ?, phone = ?, risk_level = ?,
                clinical_notes = ?, updated_at = ?
            WHERE id = ? AND doctor_id = ?
            """,
            (
                name.strip(),
                int(age),
                sex,
                mrn.strip(),
                phone.strip(),
                risk_level,
                clinical_notes.strip(),
                now_iso(),
                patient_id,
                doctor_id,
            ),
        )


def list_patients(doctor_id: int, search: str = "") -> list[dict]:
    search = f"%{search.strip()}%"
    with get_workspace_connection(doctor_id) as conn:
        rows = conn.execute(
            """
            SELECT p.*,
                   COUNT(s.id) AS scan_count,
                   MAX(s.created_at) AS latest_scan_at
            FROM patients p
            LEFT JOIN scans s ON s.patient_id = p.id
            WHERE p.doctor_id = ?
              AND (? = '%' OR p.name LIKE ? OR p.id LIKE ? OR p.mrn LIKE ?)
            GROUP BY p.id
            ORDER BY p.updated_at DESC
            """,
            (doctor_id, search, search, search, search),
        ).fetchall()
    return [dict(row) for row in rows]


def get_patient(doctor_id: int, patient_id: str | None) -> dict | None:
    if not patient_id:
        return None
    with get_workspace_connection(doctor_id) as conn:
        return as_dict(
            conn.execute(
                "SELECT * FROM patients WHERE id = ? AND doctor_id = ?",
                (patient_id, doctor_id),
            ).fetchone()
        )


def save_upload(uploaded_file, doctor_id: int, patient_id: str, scan_id: str) -> Path:
    original_name = sanitize_filename(uploaded_file.name)
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        suffix = ".jpg"
    destination = ensure_doctor_workspace(doctor_id)["uploads"] / f"{patient_id}_{scan_id}_{Path(original_name).stem}{suffix}"
    destination.write_bytes(uploaded_file.getbuffer())
    return destination


def save_annotated_image(result, doctor_id: int, patient_id: str, scan_id: str) -> Path:
    destination = ensure_doctor_workspace(doctor_id)["predictions"] / f"{patient_id}_{scan_id}_prediction.jpg"
    plotted = result.plot(pil=True)
    if isinstance(plotted, Image.Image):
        plotted.save(destination)
    else:
        Image.fromarray(plotted).save(destination)
    return destination


def tensor_to_list(value):
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    if hasattr(value, "tolist"):
        value = value.tolist()
    return value


def normalize_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


@st.cache_resource(show_spinner=False)
def load_model():
    from ultralytics import YOLO

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
    return YOLO(str(MODEL_PATH))


def extract_detections(result, model) -> list[dict]:
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    names = getattr(result, "names", None) or getattr(model, "names", {}) or {}
    cls_values = normalize_list(tensor_to_list(boxes.cls))
    conf_values = normalize_list(tensor_to_list(boxes.conf))
    xyxy_values = normalize_list(tensor_to_list(boxes.xyxy))

    detections = []
    for index, class_id in enumerate(cls_values):
        class_id = int(class_id)
        if isinstance(names, dict):
            label = names.get(class_id, f"Class {class_id}")
        else:
            label = str(class_id)

        bbox = xyxy_values[index] if index < len(xyxy_values) else []
        confidence = float(conf_values[index]) if index < len(conf_values) else 0.0
        detections.append(
            {
                "label": str(label),
                "confidence": confidence,
                "bbox": [round(float(point), 2) for point in normalize_list(bbox)],
            }
        )

    return sorted(detections, key=lambda item: item["confidence"], reverse=True)


def positive_like(label: str) -> bool:
    normalized = label.strip().lower()
    return any(token in normalized for token in ("positive", "tumor", "glioma", "meningioma", "pituitary", "yes"))


def confidence_band(confidence: float) -> str:
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.45:
        return "moderate"
    return "low"


def build_prediction_summary(detections: list[dict]) -> dict:
    positive_detections = [item for item in detections if positive_like(item["label"])]

    if positive_detections:
        best = positive_detections[0]
        count = len(positive_detections)
        region_word = "region" if count == 1 else "regions"
        return {
            "status": "Tumor-positive review",
            "tone": "positive",
            "headline": (
                f"The model detected {count} tumor-positive {region_word}. "
                f"The strongest finding is {best['label']} with {best['confidence']:.1%} confidence."
            ),
            "details": (
                f"This is a {confidence_band(best['confidence'])}-confidence AI finding. "
                "Confirm against radiology review, clinical history, and follow-up imaging before diagnosis."
            ),
            "confidence": best["confidence"],
            "label": best["label"],
            "region_count": count,
        }

    if detections:
        best = detections[0]
        return {
            "status": "No positive tumor finding",
            "tone": "negative",
            "headline": (
                f"The model did not return a tumor-positive class. "
                f"The strongest class was {best['label']} with {best['confidence']:.1%} confidence."
            ),
            "details": (
                "This result should be reviewed with the scan quality, symptoms, and clinical context. "
                "A negative AI result is not a final diagnosis."
            ),
            "confidence": best["confidence"],
            "label": best["label"],
            "region_count": len(detections),
        }

    return {
        "status": "No detection",
        "tone": "negative",
        "headline": "The model did not detect a tumor-positive region in this image.",
        "details": (
            "Review image quality and clinical context before making decisions. "
            "A negative AI result is not a final diagnosis."
        ),
        "confidence": 0.0,
        "label": "None",
        "region_count": 0,
    }


def predict_scan(image_path: Path, doctor_id: int, patient_id: str, scan_id: str, confidence_threshold: float) -> dict:
    model = load_model()
    results = model(str(image_path), conf=confidence_threshold, verbose=False)
    result = results[0]
    detections = extract_detections(result, model)
    annotated_path = save_annotated_image(result, doctor_id, patient_id, scan_id)
    summary = build_prediction_summary(detections)
    return {
        "annotated_path": str(annotated_path),
        "detections": detections,
        "summary": summary,
    }


def insert_scan(
    doctor_id: int,
    patient_id: str,
    scan_id: str,
    modality: str,
    original_filename: str,
    original_path: Path,
    prediction: dict,
    confidence_threshold: float,
) -> None:
    summary = prediction["summary"]
    with get_workspace_connection(doctor_id) as conn:
        conn.execute(
            """
            INSERT INTO scans (
                id, patient_id, doctor_id, modality, original_filename, original_path,
                prediction_path, top_label, confidence, status, summary_headline,
                summary_details, detections_json, confidence_threshold, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_id,
                patient_id,
                doctor_id,
                modality,
                original_filename,
                str(original_path),
                prediction["annotated_path"],
                summary["label"],
                float(summary["confidence"]),
                summary["status"],
                summary["headline"],
                summary["details"],
                json.dumps(prediction["detections"]),
                confidence_threshold,
                now_iso(),
            ),
        )
        conn.execute(
            "UPDATE patients SET updated_at = ? WHERE id = ? AND doctor_id = ?",
            (now_iso(), patient_id, doctor_id),
        )


def list_scans(doctor_id: int, patient_id: str | None = None, limit: int = 50) -> list[dict]:
    query = """
        SELECT s.*, p.name AS patient_name, p.mrn AS patient_mrn
        FROM scans s
        JOIN patients p ON p.id = s.patient_id
        WHERE s.doctor_id = ?
    """
    params: list = [doctor_id]
    if patient_id:
        query += " AND s.patient_id = ?"
        params.append(patient_id)
    query += " ORDER BY s.created_at DESC LIMIT ?"
    params.append(limit)

    with get_workspace_connection(doctor_id) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def latest_scan(doctor_id: int, patient_id: str) -> dict | None:
    scans = list_scans(doctor_id, patient_id, limit=1)
    return scans[0] if scans else None


def safe_unlink(path_value: str | None) -> None:
    if not path_value:
        return
    path = Path(path_value)
    try:
        if path.exists() and path.is_file():
            path.unlink()
    except OSError:
        pass


def delete_scan(doctor_id: int, scan_id: str) -> bool:
    with get_workspace_connection(doctor_id) as conn:
        scan = conn.execute(
            "SELECT * FROM scans WHERE id = ? AND doctor_id = ?",
            (scan_id, doctor_id),
        ).fetchone()
        if scan is None:
            return False
        safe_unlink(scan["original_path"])
        safe_unlink(scan["prediction_path"])
        conn.execute("DELETE FROM scans WHERE id = ? AND doctor_id = ?", (scan_id, doctor_id))
    return True


def delete_patient(doctor_id: int, patient_id: str) -> bool:
    with get_workspace_connection(doctor_id) as conn:
        patient = conn.execute(
            "SELECT * FROM patients WHERE id = ? AND doctor_id = ?",
            (patient_id, doctor_id),
        ).fetchone()
        if patient is None:
            return False
        scans = conn.execute(
            "SELECT original_path, prediction_path FROM scans WHERE patient_id = ? AND doctor_id = ?",
            (patient_id, doctor_id),
        ).fetchall()
        for scan in scans:
            safe_unlink(scan["original_path"])
            safe_unlink(scan["prediction_path"])
        conn.execute("DELETE FROM scans WHERE patient_id = ? AND doctor_id = ?", (patient_id, doctor_id))
        conn.execute("DELETE FROM patients WHERE id = ? AND doctor_id = ?", (patient_id, doctor_id))
    return True


def dashboard_stats(doctor_id: int) -> dict:
    with get_workspace_connection(doctor_id) as conn:
        patients = conn.execute("SELECT COUNT(*) FROM patients WHERE doctor_id = ?", (doctor_id,)).fetchone()[0]
        scans = conn.execute("SELECT COUNT(*) FROM scans WHERE doctor_id = ?", (doctor_id,)).fetchone()[0]
        positive = conn.execute(
            """
            SELECT COUNT(*) FROM scans
            WHERE doctor_id = ? AND lower(status) LIKE '%positive%'
            """,
            (doctor_id,),
        ).fetchone()[0]
        avg_confidence = conn.execute(
            "SELECT AVG(confidence) FROM scans WHERE doctor_id = ?",
            (doctor_id,),
        ).fetchone()[0]
    return {
        "patients": int(patients),
        "scans": int(scans),
        "positive": int(positive),
        "avg_confidence": float(avg_confidence or 0),
    }


def repair_workspace_confidentiality(doctor_id: int) -> None:
    if "doctor" in st.session_state and st.session_state.doctor and int(st.session_state.doctor.get("id")) == doctor_id:
        doctor = st.session_state.doctor
    else:
        doctor = get_doctor(doctor_id) or {}
    email = normalized_identity(doctor.get("email"))
    if email == DEFAULT_DOCTOR_EMAIL:
        return

    with get_workspace_connection(doctor_id) as conn:
        if email == "aisha@gmail.com":
            conn.execute(
                """
                DELETE FROM scans
                WHERE doctor_id = ?
                  AND patient_id IN (
                      SELECT id FROM patients
                      WHERE doctor_id = ?
                        AND (lower(name) IN ('monika', 'mounika') OR id = ?)
                  )
                """,
                (doctor_id, doctor_id, "P-20260429-26FE6"),
            )
            conn.execute(
                """
                DELETE FROM patients
                WHERE doctor_id = ?
                  AND (lower(name) IN ('monika', 'mounika') OR id = ?)
                """,
                (doctor_id, "P-20260429-26FE6"),
            )

        conn.execute(
            """
            DELETE FROM scans
            WHERE doctor_id = ?
              AND patient_id NOT IN (
                  SELECT id FROM patients WHERE doctor_id = ?
              )
            """,
            (doctor_id, doctor_id),
        )


def migrate_workspace_for_doctor(doctor_id: int) -> None:
    paths = ensure_doctor_workspace(doctor_id)
    if paths["migration_flag"].exists():
        if not st.session_state.get(f"workspace_repaired_{doctor_id}"):
            repair_workspace_confidentiality(doctor_id)
            st.session_state[f"workspace_repaired_{doctor_id}"] = True
        return

    if "doctor" in st.session_state and st.session_state.doctor and int(st.session_state.doctor.get("id")) == doctor_id:
        doctor = st.session_state.doctor
    else:
        doctor = get_doctor(doctor_id) or {}

    copied_patients = 0
    allowed_patient_ids: set[str] = set()
    with get_workspace_connection(doctor_id) as target, get_connection() as source:
        if table_exists(source, "patients"):
            for row in source.execute("SELECT * FROM patients WHERE doctor_id = ?", (doctor_id,)).fetchall():
                if not legacy_patient_matches_doctor(row, doctor):
                    continue
                allowed_patient_ids.add(row["id"])
                target.execute(
                    """
                    INSERT INTO patients (
                        id, doctor_id, mrn, name, age, sex, phone, risk_level,
                        clinical_notes, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        row["id"],
                        doctor_id,
                        row["mrn"],
                        row["name"],
                        row["age"],
                        row["sex"],
                        row["phone"],
                        row["risk_level"],
                        row["clinical_notes"],
                        row["created_at"],
                        row["updated_at"],
                    ),
                )
                copied_patients += 1

        if table_exists(source, "scans"):
            for row in source.execute("SELECT * FROM scans WHERE doctor_id = ?", (doctor_id,)).fetchall():
                if row["patient_id"] not in allowed_patient_ids:
                    continue
                target.execute(
                    """
                    INSERT INTO scans (
                        id, patient_id, doctor_id, modality, original_filename, original_path,
                        prediction_path, top_label, confidence, status, summary_headline,
                        summary_details, detections_json, confidence_threshold, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        row["id"],
                        row["patient_id"],
                        doctor_id,
                        row["modality"],
                        row["original_filename"],
                        row["original_path"],
                        row["prediction_path"],
                        row["top_label"],
                        row["confidence"],
                        row["status"],
                        row["summary_headline"],
                        row["summary_details"],
                        row["detections_json"],
                        row["confidence_threshold"],
                        row["created_at"],
                    ),
                )

    if copied_patients == 0 and doctor.get("email", "").lower() == DEFAULT_DOCTOR_EMAIL and LEGACY_RECORDS_FILE.exists():
        migrate_legacy_json_to_workspace(doctor_id)

    repair_workspace_confidentiality(doctor_id)
    st.session_state[f"workspace_repaired_{doctor_id}"] = True
    paths["migration_flag"].write_text(now_iso(), encoding="utf-8")


def migrate_legacy_json_to_workspace(doctor_id: int) -> None:
    try:
        legacy_records = json.loads(LEGACY_RECORDS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    with get_workspace_connection(doctor_id) as conn:
        for record in legacy_records:
            patient_id = record.get("id") or new_patient_id()
            conn.execute(
                """
                INSERT INTO patients (
                    id, doctor_id, mrn, name, age, sex, phone, risk_level,
                    clinical_notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    patient_id,
                    doctor_id,
                    record.get("patient_code", ""),
                    record.get("name", "Imported patient"),
                    int(record.get("age", 0) or 0),
                    record.get("sex", "Prefer not to say"),
                    "",
                    "Imported",
                    record.get("clinical_notes", ""),
                    record.get("created_at", now_iso()),
                    record.get("updated_at", now_iso()),
                ),
            )

            for upload in record.get("uploads", []):
                prediction = upload.get("prediction", {})
                summary = prediction.get("summary", {})
                scan_id = new_scan_id()
                conn.execute(
                    """
                    INSERT INTO scans (
                        id, patient_id, doctor_id, modality, original_filename, original_path,
                        prediction_path, top_label, confidence, status, summary_headline,
                        summary_details, detections_json, confidence_threshold, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        scan_id,
                        patient_id,
                        doctor_id,
                        "MRI",
                        Path(prediction.get("image_path", upload.get("image_path", ""))).name,
                        prediction.get("image_path", upload.get("image_path", "")),
                        prediction.get("annotated_path", ""),
                        summary.get("label", ""),
                        float(summary.get("confidence", 0) or 0),
                        summary.get("status", "Imported"),
                        summary.get("headline", "Imported legacy prediction."),
                        summary.get("details", ""),
                        json.dumps(prediction.get("detections", [])),
                        float(prediction.get("confidence_threshold", 0.25) or 0.25),
                        prediction.get("predicted_at", upload.get("uploaded_at", now_iso())),
                    ),
                )


def sign_in_doctor(doctor: dict) -> None:
    migrate_workspace_for_doctor(int(doctor["id"]))
    st.session_state.authenticated = True
    st.session_state.doctor_id = int(doctor["id"])
    st.session_state.selected_patient_id = None
    st.session_state.active_page = "Command Center"


def sign_out() -> None:
    for key in (
        "authenticated",
        "doctor_id",
        "selected_patient_id",
        "selected_scan_id",
        "active_page",
        "pending_page",
        "report_notice",
    ):
        st.session_state.pop(key, None)
    st.session_state.auth_mode = "Access workspace"
    st.rerun()


def auth_view() -> None:
    copy_col, access_col = st.columns([1.08, 0.92], gap="large")

    with copy_col:
        st.markdown(
            """
            <div class="auth-copy">
                <div class="eyebrow">NeuroDesk Clinical AI</div>
                <h1>Brain tumor screening, built like software.</h1>
                <p class="hero-copy">
                    Secure doctor accounts, patient registry, local imaging dataset storage,
                    model-assisted scan review, and exportable clinical summaries in one workspace.
                </p>
                <div class="hero-meta">
                    <span class="pill">SQLite records</span>
                    <span class="pill">Local scan vault</span>
                    <span class="pill">YOLO model inference</span>
                    <span class="pill">Audit-ready summaries</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with access_col:
        with st.container(border=True):
            mode_options = ["Access workspace", "New clinician"]
            if st.session_state.get("auth_mode") not in mode_options:
                st.session_state.auth_mode = mode_options[0]

            mode = st.radio(
                "Workspace access mode",
                mode_options,
                horizontal=True,
                label_visibility="collapsed",
                key="auth_mode",
            )

            if mode == "Access workspace":
                st.markdown("### Workspace Access")
                st.caption("Enter your clinical workspace. Press Enter from the password field to continue.")
                with st.form("login_form"):
                    email = st.text_input("Email", placeholder="doctor@hospital.com")
                    password = st.text_input("Password", type="password")
                    submitted = st.form_submit_button("Enter workspace", type="primary", width="stretch")
                if submitted:
                    ok, message, doctor = authenticate_doctor(email, password)
                    if ok and doctor:
                        sign_in_doctor(doctor)
                        st.rerun()
                    else:
                        st.error(message)

            else:
                st.markdown("### Register Clinician")
                st.caption("Create a private workspace with its own patient database.")
                with st.form("signup_form"):
                    name = st.text_input("Full name", placeholder="Dr. Aisha Khan")
                    email = st.text_input("Work email", placeholder="doctor@hospital.com")
                    hospital = st.text_input("Hospital / clinic", placeholder="NeuroCare Center")
                    specialty = st.text_input("Specialty", placeholder="Radiology, Neurology, Oncology")
                    password = st.text_input("Password", type="password")
                    confirm_password = st.text_input("Confirm password", type="password")
                    submitted = st.form_submit_button("Create secure profile", type="primary", width="stretch")

                if submitted:
                    if not name.strip() or not email.strip() or not password:
                        st.warning("Name, email, and password are required.")
                    elif len(password) < 8:
                        st.warning("Use at least 8 characters for the password.")
                    elif password != confirm_password:
                        st.warning("Passwords do not match.")
                    else:
                        ok, message, doctor = create_doctor(name, email, password, hospital, specialty)
                        if ok and doctor:
                            sign_in_doctor(doctor)
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)


def render_topbar(doctor: dict) -> None:
    name = escape(doctor.get("name", "Doctor"))
    hospital = escape(doctor.get("hospital") or "Clinical workspace")
    st.markdown(
        f"""
        <div class="topbar">
            <div class="brand">
                <div class="brand-mark">ND</div>
                <div>
                    <div class="brand-title">NeuroDesk</div>
                    <div class="brand-subtitle">Brain tumor imaging workspace</div>
                </div>
            </div>
            <div class="doctor-chip">{name} - {hospital}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    nav_col, theme_col, action_col = st.columns([5, 1.2, 1])
    with nav_col:
        st.radio(
            "Navigation",
            ["Command Center", "Patients", "Imaging", "Reports", "Data Vault"],
            horizontal=True,
            label_visibility="collapsed",
            key="active_page",
        )
    with theme_col:
        light_mode = st.session_state.get("light_mode", False)
        theme_label = "Light" if light_mode else "Dark"
        theme_icon = ":material/light_mode:" if light_mode else ":material/dark_mode:"
        if st.button(theme_label, key="theme_mode_button", icon=theme_icon, width="stretch"):
            st.session_state.light_mode = not light_mode
            st.rerun()
    with action_col:
        if st.button("Sign out", width="stretch"):
            sign_out()


def metric_card(label: str, value: str, note: str = "") -> str:
    return (
        '<div class="metric-card">'
        f'<div class="metric-label">{escape(label)}</div>'
        f'<div class="metric-value">{escape(value)}</div>'
        f'<div class="metric-note">{escape(note)}</div>'
        "</div>"
    )


def render_metric_grid(stats: dict) -> None:
    avg_confidence = f"{stats['avg_confidence']:.1%}"
    cards = "".join(
        [
            metric_card("Patients", str(stats["patients"]), "Registered records"),
            metric_card("Scans", str(stats["scans"]), "Images analyzed"),
            metric_card("Positive Reviews", str(stats["positive"]), "Tumor-positive model results"),
            metric_card("Avg Confidence", avg_confidence, "Across all scans"),
        ]
    )
    st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)


def render_patient_banner(patient: dict | None) -> None:
    if not patient:
        st.markdown(
            """
            <div class="patient-banner">
                <div class="patient-name">No patient selected</div>
                <div class="patient-meta">Create or select a patient to begin scan analysis.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    mrn = f" - MRN {escape(patient['mrn'])}" if patient.get("mrn") else ""
    st.markdown(
        f"""
        <div class="patient-banner">
            <div class="patient-name">{escape(patient["name"])}</div>
            <div class="patient-meta">
                {escape(patient["id"])} - {int(patient["age"])} years - {escape(patient["sex"])}{mrn}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    normalized = (status or "").lower()
    if "positive" in normalized:
        style = "status-positive"
    elif "negative" in normalized or "no detection" in normalized:
        style = "status-negative"
    else:
        style = "status-review"
    return f'<span class="status-badge {style}">{escape(status or "Pending")}</span>'


def patient_selectbox(doctor_id: int, label: str = "Patient") -> dict | None:
    patients = list_patients(doctor_id)
    if not patients:
        return None

    selected_id = st.session_state.get("selected_patient_id")
    valid_ids = {patient["id"] for patient in patients}
    if selected_id not in valid_ids:
        selected_id = patients[0]["id"]
        st.session_state.selected_patient_id = selected_id

    selected = st.selectbox(
        label,
        options=[patient["id"] for patient in patients],
        index=[patient["id"] for patient in patients].index(selected_id),
        format_func=lambda patient_id: next(
            f"{patient['name']} - {patient['id']}" for patient in patients if patient["id"] == patient_id
        ),
    )
    st.session_state.selected_patient_id = selected
    return get_patient(doctor_id, selected)


def command_center(doctor: dict) -> None:
    doctor_id = int(doctor["id"])
    stats = dashboard_stats(doctor_id)
    latest_scans = list_scans(doctor_id, limit=6)

    st.markdown(
        """
        <div class="hero-panel">
            <div class="eyebrow">Clinical Command Center</div>
            <h1>NeuroDesk</h1>
            <p class="hero-copy">
                Patient imaging, CNN-assisted tumor review, and local dataset governance
                for a focused clinical workflow.
            </p>
            <div class="hero-meta">
                <span class="pill">Model: exp.pt</span>
                <span class="pill">Storage: patient_data</span>
                <span class="pill">Database: SQLite</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_metric_grid(stats)

    col_a, col_b = st.columns([1.05, 0.95], gap="large")
    with col_a:
        st.markdown('<div class="section-title"><div><h2>Recent Model Reviews</h2><div class="section-kicker">Latest scan results</div></div></div>', unsafe_allow_html=True)
        if latest_scans:
            st.dataframe(
                [
                    {
                        "Patient": scan["patient_name"],
                        "Modality": scan["modality"],
                        "Status": scan["status"],
                        "Confidence": f"{float(scan['confidence'] or 0):.1%}",
                        "Reviewed": readable_time(scan["created_at"]),
                    }
                    for scan in latest_scans
                ],
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("No scans have been analyzed yet.")

    with col_b:
        st.markdown('<div class="section-title"><div><h2>Active Patient</h2><div class="section-kicker">Current workspace context</div></div></div>', unsafe_allow_html=True)
        patient = get_patient(doctor_id, st.session_state.get("selected_patient_id")) or patient_selectbox(doctor_id, "Open patient")
        render_patient_banner(patient)
        if patient:
            scan = latest_scan(doctor_id, patient["id"])
            if scan:
                st.markdown(
                    f"""
                    <div class="report-card">
                        <div class="report-title">Latest AI Summary</div>
                        <div>{status_badge(scan["status"])}</div>
                        <p class="report-body">{escape(scan["summary_headline"])}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info("This patient has no scan reviews yet.")


def patient_form(doctor_id: int) -> None:
    st.markdown('<div class="section-title"><div><h2>Create Patient Record</h2><div class="section-kicker">Patient demographics and clinical notes</div></div></div>', unsafe_allow_html=True)
    with st.form("create_patient_form"):
        col_a, col_b, col_c = st.columns([2, 1, 1])
        with col_a:
            name = st.text_input("Patient name")
        with col_b:
            age = st.number_input("Age", min_value=0, max_value=120, value=35)
        with col_c:
            sex = st.selectbox("Sex", ["Female", "Male", "Other", "Prefer not to say"])

        col_d, col_e, col_f = st.columns([1, 1, 1])
        with col_d:
            mrn = st.text_input("Hospital ID / MRN")
        with col_e:
            phone = st.text_input("Phone")
        with col_f:
            risk_level = st.selectbox("Priority", ["Routine", "Follow-up", "Urgent", "Imported"])

        clinical_notes = st.text_area("Clinical notes", placeholder="Symptoms, prior findings, medications, referring notes")
        submitted = st.form_submit_button("Create record", type="primary", width="stretch")

    if submitted:
        if not name.strip():
            st.warning("Patient name is required.")
            return
        patient_id = create_patient(doctor_id, name, int(age), sex, mrn, phone, risk_level, clinical_notes)
        st.session_state.selected_patient_id = patient_id
        st.success("Patient record created.")
        st.rerun()


def edit_patient_form(doctor_id: int, patient: dict) -> None:
    st.markdown('<div class="section-title"><div><h2>Patient Profile</h2><div class="section-kicker">Record details</div></div></div>', unsafe_allow_html=True)
    with st.form(f"edit_patient_{patient['id']}"):
        col_a, col_b, col_c = st.columns([2, 1, 1])
        with col_a:
            name = st.text_input("Patient name", value=patient.get("name", ""))
        with col_b:
            age = st.number_input("Age", min_value=0, max_value=120, value=int(patient.get("age", 35)))
        with col_c:
            sex_options = ["Female", "Male", "Other", "Prefer not to say"]
            sex_value = patient.get("sex", "Female")
            sex = st.selectbox(
                "Sex",
                sex_options,
                index=sex_options.index(sex_value) if sex_value in sex_options else 0,
            )

        col_d, col_e, col_f = st.columns([1, 1, 1])
        with col_d:
            mrn = st.text_input("Hospital ID / MRN", value=patient.get("mrn", ""))
        with col_e:
            phone = st.text_input("Phone", value=patient.get("phone", ""))
        with col_f:
            priority_options = ["Routine", "Follow-up", "Urgent", "Imported"]
            priority_value = patient.get("risk_level") or "Routine"
            risk_level = st.selectbox(
                "Priority",
                priority_options,
                index=priority_options.index(priority_value) if priority_value in priority_options else 0,
            )

        clinical_notes = st.text_area("Clinical notes", value=patient.get("clinical_notes", ""))
        submitted = st.form_submit_button("Save changes", type="primary", width="stretch")

    if submitted:
        if not name.strip():
            st.warning("Patient name is required.")
            return
        update_patient(doctor_id, patient["id"], name, int(age), sex, mrn, phone, risk_level, clinical_notes)
        st.success("Patient profile updated.")
        st.rerun()


def patients_page(doctor: dict) -> None:
    doctor_id = int(doctor["id"])
    patient_form(doctor_id)

    st.markdown('<div class="section-title"><div><h2>Patient Registry</h2><div class="section-kicker">Search and manage records</div></div></div>', unsafe_allow_html=True)
    search = st.text_input("Search patients", placeholder="Name, record ID, or MRN")
    patients = list_patients(doctor_id, search)
    if not patients:
        st.info("No patient records found.")
        return

    selected_id = st.selectbox(
        "Open record",
        options=[patient["id"] for patient in patients],
        format_func=lambda patient_id: next(
            f"{patient['name']} - {patient['id']}" for patient in patients if patient["id"] == patient_id
        ),
    )
    st.session_state.selected_patient_id = selected_id
    selected_patient = get_patient(doctor_id, selected_id)
    render_patient_banner(selected_patient)

    st.dataframe(
        [
            {
                "Patient": patient["name"],
                "Record ID": patient["id"],
                "MRN": patient["mrn"],
                "Priority": patient["risk_level"],
                "Scans": patient["scan_count"],
                "Last scan": readable_time(patient["latest_scan_at"]),
            }
            for patient in patients
        ],
        hide_index=True,
        width="stretch",
    )

    if selected_patient:
        edit_patient_form(doctor_id, selected_patient)
        with st.expander("Delete patient record"):
            st.warning("This removes the patient, all scan records, and the locally stored images for this profile.")
            confirm_delete = st.checkbox(
                f"I understand and want to delete {selected_patient['name']}",
                key=f"confirm_delete_patient_{selected_patient['id']}",
            )
            if st.button(
                "Delete patient and scans",
                disabled=not confirm_delete,
                key=f"delete_patient_{selected_patient['id']}",
            ):
                if delete_patient(doctor_id, selected_patient["id"]):
                    st.session_state.selected_patient_id = None
                    st.success("Patient record deleted.")
                    st.rerun()
                else:
                    st.error("Patient record could not be found.")


def imaging_page(doctor: dict) -> None:
    doctor_id = int(doctor["id"])
    patient = patient_selectbox(doctor_id, "Select patient")
    render_patient_banner(patient)

    if not patient:
        st.info("Create a patient record before uploading scan images.")
        return

    col_a, col_b = st.columns([1, 1], gap="large")
    with col_a:
        st.markdown('<div class="section-title"><div><h2>Imaging Intake</h2><div class="section-kicker">Upload MRI, X-ray, or CT images</div></div></div>', unsafe_allow_html=True)
        modality = st.selectbox("Modality", ["MRI", "X-ray", "CT", "Other"])
        confidence_threshold = st.slider("Detection threshold", 0.10, 0.90, 0.25, 0.05)
        uploaded_file = st.file_uploader("Scan image", type=["jpg", "jpeg", "png"])

    with col_b:
        st.markdown('<div class="section-title"><div><h2>Preview</h2><div class="section-kicker">Image ready for model review</div></div></div>', unsafe_allow_html=True)
        if uploaded_file is not None:
            try:
                image = Image.open(uploaded_file)
                st.image(image, caption=uploaded_file.name, width="stretch")
            except Exception:
                st.error("The uploaded file could not be opened as an image.")
                return
        else:
            st.info("Upload a JPG or PNG scan to continue.")

    if st.button("Run CNN Model", type="primary", disabled=uploaded_file is None, width="stretch"):
        scan_id = new_scan_id()
        with st.spinner("Running model inference and generating clinical summary..."):
            original_path = save_upload(uploaded_file, doctor_id, patient["id"], scan_id)
            prediction = predict_scan(original_path, doctor_id, patient["id"], scan_id, confidence_threshold)
            insert_scan(
                doctor_id=doctor_id,
                patient_id=patient["id"],
                scan_id=scan_id,
                modality=modality,
                original_filename=sanitize_filename(uploaded_file.name),
                original_path=original_path,
                prediction=prediction,
                confidence_threshold=confidence_threshold,
            )
        st.session_state.pending_page = "Reports"
        st.session_state.selected_scan_id = scan_id
        st.session_state.report_notice = f"Report {scan_id} generated successfully."
        st.rerun()


def scan_report_payload(patient: dict, scan: dict) -> dict:
    return {
        "patient": {
            "id": patient["id"],
            "name": patient["name"],
            "age": patient["age"],
            "sex": patient["sex"],
            "mrn": patient.get("mrn"),
            "priority": patient.get("risk_level"),
            "clinical_notes": patient.get("clinical_notes"),
        },
        "scan": {
            "id": scan["id"],
            "modality": scan["modality"],
            "status": scan["status"],
            "top_label": scan["top_label"],
            "confidence": scan["confidence"],
            "summary": {
                "headline": scan["summary_headline"],
                "details": scan["summary_details"],
            },
            "detections": json.loads(scan.get("detections_json") or "[]"),
            "original_path": scan["original_path"],
            "prediction_path": scan["prediction_path"],
            "reviewed_at": scan["created_at"],
        },
    }


def render_report(patient: dict, scan: dict) -> None:
    confidence_text = f"{float(scan['confidence'] or 0):.1%}"
    st.markdown(
        f"""
        <div class="report-card">
            <div class="report-title">AI Clinical Summary</div>
            <div>{status_badge(scan["status"])}</div>
            <p class="report-body">{escape(scan["summary_headline"])}</p>
            <p class="report-body">{escape(scan["summary_details"])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    report_cards = "".join(
        [
            metric_card("Status", scan["status"] or "Pending", "Model review state"),
            metric_card("Finding", scan["top_label"] or "None", "Top model class"),
            metric_card("Confidence", confidence_text, "Top class confidence"),
            metric_card("Modality", scan["modality"], readable_time(scan["created_at"])),
        ]
    )
    st.markdown(f'<div class="metric-grid">{report_cards}</div>', unsafe_allow_html=True)

    image_a, image_b = st.columns(2, gap="large")
    with image_a:
        st.markdown("### Original Scan")
        if scan["original_path"] and Path(scan["original_path"]).exists():
            st.image(scan["original_path"], width="stretch")
        else:
            st.warning("Original image is missing from local storage.")
    with image_b:
        st.markdown("### Model Output")
        if scan["prediction_path"] and Path(scan["prediction_path"]).exists():
            st.image(scan["prediction_path"], width="stretch")
        else:
            st.warning("Prediction image is missing from local storage.")

    detections = json.loads(scan.get("detections_json") or "[]")
    if detections:
        st.markdown("### Detection Details")
        st.dataframe(
            [
                {
                    "Class": item["label"],
                    "Confidence": f"{float(item['confidence']):.1%}",
                    "Bounding box": item["bbox"],
                }
                for item in detections
            ],
            hide_index=True,
            width="stretch",
        )

    st.download_button(
        "Download clinical summary",
        data=json.dumps(scan_report_payload(patient, scan), indent=2),
        file_name=f"{scan['id']}_clinical_summary.json",
        mime="application/json",
        width="stretch",
    )
    st.caption("Decision support only. Final interpretation must come from qualified clinical review.")


def reports_page(doctor: dict) -> None:
    doctor_id = int(doctor["id"])
    patient = patient_selectbox(doctor_id, "Select patient")
    render_patient_banner(patient)
    if not patient:
        st.info("No patient selected.")
        return

    scans = list_scans(doctor_id, patient["id"], limit=30)
    if not scans:
        st.info("This patient has no scan reports yet.")
        return

    preferred_scan_id = st.session_state.get("selected_scan_id")
    scan_ids = [scan["id"] for scan in scans]
    selector_key = f"scan_selector_{patient['id']}"
    if st.session_state.get(selector_key) not in (None, *scan_ids):
        st.session_state.pop(selector_key, None)
    selected_scan_id = st.selectbox(
        "Open scan report",
        options=scan_ids,
        index=scan_ids.index(preferred_scan_id) if preferred_scan_id in scan_ids else 0,
        format_func=lambda scan_id: next(
            f"{scan['modality']} - {readable_time(scan['created_at'])} - {scan['status']}"
            for scan in scans
            if scan["id"] == scan_id
        ),
        key=selector_key,
    )
    st.session_state.selected_scan_id = selected_scan_id
    scan = next(item for item in scans if item["id"] == selected_scan_id)
    render_report(patient, scan)

    with st.expander("Delete this scan report"):
        st.warning("This removes the scan report and its original/model-output images from this doctor's workspace.")
        confirm_scan_delete = st.checkbox(
            f"I understand and want to delete scan {scan['id']}",
            key=f"confirm_delete_scan_{scan['id']}",
        )
        if st.button("Delete scan report", disabled=not confirm_scan_delete, key=f"delete_scan_{scan['id']}"):
            if delete_scan(doctor_id, scan["id"]):
                st.session_state.pop("selected_scan_id", None)
                st.success("Scan report deleted.")
                st.rerun()
            else:
                st.error("Scan report could not be found.")

    st.markdown('<div class="section-title"><div><h2>Report History</h2><div class="section-kicker">All model reviews for this patient</div></div></div>', unsafe_allow_html=True)
    st.dataframe(
        [
            {
                "Scan ID": item["id"],
                "Modality": item["modality"],
                "Status": item["status"],
                "Finding": item["top_label"],
                "Confidence": f"{float(item['confidence'] or 0):.1%}",
                "Reviewed": readable_time(item["created_at"]),
            }
            for item in scans
        ],
        hide_index=True,
                width="stretch",
    )


def data_vault_page(doctor: dict) -> None:
    doctor_id = int(doctor["id"])
    stats = dashboard_stats(doctor_id)
    scans = list_scans(doctor_id, limit=100)
    paths = ensure_doctor_workspace(doctor_id)

    st.markdown(
        """
        <div class="hero-panel">
            <div class="eyebrow">Dataset Storage</div>
            <h1>Local Data Vault</h1>
            <p class="hero-copy">
                Application records, uploaded images, and annotated model outputs are stored locally
                inside the project workspace.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_metric_grid(stats)

    # Removed path rows to hide directory data from the UI
    st.markdown('<div class="section-title"><div><h2>Dataset Index</h2><div class="section-kicker">Images and predictions saved by the app</div></div></div>', unsafe_allow_html=True)
    if scans:
        st.dataframe(
            [
                {
                    "Patient": scan["patient_name"],
                    "Scan ID": scan["id"],
                    "Original image": scan["original_path"],
                    "Prediction image": scan["prediction_path"],
                    "Status": scan["status"],
                    "Created": readable_time(scan["created_at"]),
                }
                for scan in scans
            ],
            hide_index=True,
            width="stretch",
        )

        st.markdown('<div class="section-title"><div><h2>Image Viewer</h2><div class="section-kicker">Open original and model-output images from this profile only</div></div></div>', unsafe_allow_html=True)
        selected_vault_scan_id = st.selectbox(
            "Open stored image pair",
            options=[scan["id"] for scan in scans],
            format_func=lambda scan_id: next(
                f"{scan['patient_name']} - {scan['modality']} - {readable_time(scan['created_at'])}"
                for scan in scans
                if scan["id"] == scan_id
            ),
            key=f"vault_scan_viewer_{doctor_id}",
        )
        selected_scan = next(scan for scan in scans if scan["id"] == selected_vault_scan_id)
        preview_a, preview_b = st.columns(2, gap="large")
        with preview_a:
            st.markdown("### Original Image")
            if selected_scan["original_path"] and Path(selected_scan["original_path"]).exists():
                st.image(selected_scan["original_path"], width="stretch")
            else:
                st.warning("Original image file is missing.")
        with preview_b:
            st.markdown("### Model Output")
            if selected_scan["prediction_path"] and Path(selected_scan["prediction_path"]).exists():
                st.image(selected_scan["prediction_path"], width="stretch")
            else:
                st.warning("Prediction image file is missing.")
    else:
        st.info("No images have been stored yet.")


def dashboard(doctor: dict) -> None:
    pending_page = st.session_state.pop("pending_page", None)
    if pending_page:
        st.session_state.active_page = pending_page

    render_topbar(doctor)

    report_notice = st.session_state.pop("report_notice", None)
    if report_notice:
        st.toast(report_notice)
        st.success(report_notice)

    page = st.session_state.get("active_page", "Command Center")

    if page == "Command Center":
        command_center(doctor)
    elif page == "Patients":
        patients_page(doctor)
    elif page == "Imaging":
        imaging_page(doctor)
    elif page == "Reports":
        reports_page(doctor)
    elif page == "Data Vault":
        data_vault_page(doctor)


def main() -> None:
    st.set_page_config(page_title="NeuroDesk", layout="wide", initial_sidebar_state="collapsed")
    ensure_storage()
    
    # Run DB migration and demo doctor setup only once per session to reduce latency
    if not st.session_state.get("db_initialized"):
        init_db()
        ensure_demo_doctor()
        st.session_state.db_initialized = True
        
    reset_session_on_upgrade()
    page_style()
    render_neural_background()

    if not st.session_state.get("authenticated"):
        auth_view()
        return

    # Cache the doctor profile in session state to avoid querying the DB on every single user click
    doctor_id = st.session_state.get("doctor_id")
    if "doctor" not in st.session_state or st.session_state.doctor is None or st.session_state.doctor.get("id") != doctor_id:
        st.session_state.doctor = get_doctor(doctor_id)

    doctor = st.session_state.doctor
    if not doctor:
        sign_out()
        return

    migrate_workspace_for_doctor(int(doctor["id"]))
    dashboard(doctor)


if __name__ == "__main__":
    main()
