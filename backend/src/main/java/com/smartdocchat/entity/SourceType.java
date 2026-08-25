package com.smartdocchat.entity;

/**
 * Provenance of a document in the system.
 *
 * USER     – uploaded by an end user (default for every upload).
 * OFFICIAL – ingested from a verified official legal source.
 * FIXTURE  – synthetic evaluation/test data; never real legal truth.
 */
public enum SourceType {
    OFFICIAL,
    USER,
    FIXTURE
}