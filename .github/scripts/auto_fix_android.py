#!/usr/bin/env python3
"""
Auto-Fix Script for Android Build Errors
Analyzes Gradle build output and applies fixes for common issues.
"""
import re, os, sys, subprocess
from pathlib import Path

BUILD_LOG = sys.argv[1] if len(sys.argv) > 1 else "build.log"
PROJECT_DIR = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")

FIXES_APPLIED = 0

def log(msg):
    print(f"[FIX] {msg}")

def fix_file(path, old, new):
    """Replace text in a file."""
    p = PROJECT_DIR / path
    if not p.exists():
        return False
    content = p.read_text(encoding="utf-8", errors="ignore")
    if old not in content:
        return False
    p.write_text(content.replace(old, new), encoding="utf-8")
    log(f"Fixed {path}: {old[:40]}...")
    global FIXES_APPLIED
    FIXES_APPLIED += 1
    return True

with open(BUILD_LOG, "r", encoding="utf-8", errors="ignore") as f:
    log_text = f.read()

# ─── Fix 1: SDK version not installed ───
m = re.search(r"installed SDK version:\s*(\d+)", log_text)
if m:
    installed_sdk = m.group(1)
    log(f"Detected installed SDK: {installed_sdk}")
    fix_file("app/build.gradle.kts",
             "compileSdk = 35",
             f"compileSdk = {installed_sdk}")
    fix_file("app/build.gradle.kts",
             "targetSdk = 35",
             f"targetSdk = {installed_sdk}")

# ─── Fix 2: Build tools version ───
m = re.search(r"build-tools;([\d.]+)", log_text)
if m and "not installed" in log_text:
    bt = m.group(1)
    log(f"Build tools {bt} not found, using latest")
    fix_file("app/build.gradle.kts",
             f'packages: \'platforms;android-35 build-tools;35.0.0\'',
             f'packages: \'platforms;android-35 build-tools;{bt}\'')

# ─── Fix 3: Java version mismatch ───
if "Unsupported class file major version" in log_text:
    m = re.search(r"major version (\d+)", log_text)
    if m:
        ver = {"61": "17", "65": "21", "55": "11"}.get(m.group(1), "17")
        log(f"Java version mismatch, switching to Java {ver}")
        fix_file(".github/workflows/android-build.yml",
                 "java-version: '17'",
                 f"java-version: '{ver}'")

# ─── Fix 4: Missing dependency ───
for pattern, dep in [
    (r"Unresolved reference:\s*(\w+)", None),
    (r"Cannot find.*?([\w.-]+:[\w.-]+:[\d.]+)", None),
]:
    for m in re.finditer(pattern, log_text):
        name = m.group(1)
        log(f"Missing dependency: {name}")

# ─── Fix 5: Compose compiler / Kotlin version mismatch ───
if "Compose compiler" in log_text and "incompatible" in log_text:
    log("Compose compiler version mismatch detected")
    fix_file("app/build.gradle.kts",
             'id("org.jetbrains.kotlin.plugin.compose") version "2.0.21" apply false',
             'id("org.jetbrains.kotlin.plugin.compose") version "2.1.0" apply false')
    fix_file("app/build.gradle.kts",
             'id("org.jetbrains.kotlin.android") version "2.0.21" apply false',
             'id("org.jetbrains.kotlin.android") version "2.1.0" apply false')

# ─── Fix 6: Gradle version too old ───
if "Minimum supported Gradle version" in log_text:
    m = re.search(r"Minimum supported Gradle version is ([\d.]+)", log_text)
    if m:
        ver = m.group(1)
        log(f"Upgrading Gradle to {ver}")
        fix_file("gradle/wrapper/gradle-wrapper.properties",
                 "gradle-8.7-bin.zip",
                 f"gradle-{ver}-bin.zip")

# ─── Fix 7: Duplicate class / packaging conflict ───
if "Duplicate class" in log_text:
    log("Duplicate class detected - adding packaging exclusions")
    build_file = PROJECT_DIR / "app/build.gradle.kts"
    content = build_file.read_text(encoding="utf-8", errors="ignore")
    if "packaging" not in content:
        exclusion_block = """
android {
    packaging {
        resources {
            excludes += setOf(
                "META-INF/DEPENDENCIES",
                "META-INF/LICENSE*",
                "META-INF/NOTICE*",
            )
        }
    }
}"""
        # Insert before dependencies block
        content = content.replace("dependencies {", exclusion_block + "\ndependencies {")
        build_file.write_text(content, encoding="utf-8")
        log("Added packaging exclusions")
        FIXES_APPLIED += 1

# ─── Fix 8: Namespace not set ───
if "Namespace not specified" in log_text:
    build_file = PROJECT_DIR / "app/build.gradle.kts"
    content = build_file.read_text(encoding="utf-8", errors="ignore")
    if 'namespace = "com.cryptoquant.ai"' not in content:
        content = content.replace(
            "compileSdk = 35",
            'namespace = "com.cryptoquant.ai"\n    compileSdk = 35'
        )
        build_file.write_text(content, encoding="utf-8")
        log("Added namespace declaration")
        FIXES_APPLIED += 1

# ─── Fix 9: Coroutines / lifecycle version ───
if "lifecycle" in log_text.lower() and "unresolved" in log_text.lower():
    log("Lifecycle dependency issue - updating versions")
    fix_file("app/build.gradle.kts",
             'androidx.lifecycle:lifecycle-runtime-ktx:2.8.7',
             'androidx.lifecycle:lifecycle-runtime-ktx:2.9.0')
    fix_file("app/build.gradle.kts",
             'androidx.activity:activity-compose:1.9.3',
             'androidx.activity:activity-compose:1.10.0')

# ─── Fix 10: Generic - try cleaning and rebuilding ───
if FIXES_APPLIED == 0 and "FAILURE" in log_text:
    log("No specific fix matched. Attempting Gradle clean...")
    # Add clean step by touching a settings change
    fix_file("gradle.properties",
             "# Auto-fix",
             "# Auto-fix clean trigger\norg.gradle.caching=true")

# ─── Summary ───
if FIXES_APPLIED > 0:
    print(f"\nCHANGES_APPLIED: {FIXES_APPLIED} fixes applied")
else:
    print("\nNO_FIXES_APPLIED: No automated fixes matched the error")
    # Print the last 20 lines of the error for manual inspection
    lines = log_text.strip().split("\n")
    error_lines = [l for l in lines if "error" in l.lower() or "fail" in l.lower() or "exception" in l.lower()]
    print("\nLast errors:")
    for l in error_lines[-10:]:
        print(f"  {l[:200]}")
