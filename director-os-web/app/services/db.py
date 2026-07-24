from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import DATA_ROOT, DATABASE_PATH


def ensure_data_dir() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    ensure_data_dir()
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialize_database() -> None:
    ensure_data_dir()
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'local',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS shot_packs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                shot_id TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL,
                purpose TEXT NOT NULL DEFAULT 'UNKNOWN',
                status TEXT NOT NULL DEFAULT 'seeded',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS generated_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_pack_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                renderer TEXT NOT NULL DEFAULT 'generic',
                status TEXT NOT NULL DEFAULT 'review_only',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(shot_pack_id, filename),
                FOREIGN KEY(shot_pack_id) REFERENCES shot_packs(id)
            );

            CREATE TABLE IF NOT EXISTS approval_gates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_pack_id INTEGER NOT NULL,
                renderer_selected TEXT NOT NULL,
                exact_references TEXT NOT NULL,
                privacy_warning_acknowledged INTEGER NOT NULL DEFAULT 0,
                spend_upload_limit TEXT NOT NULL,
                final_request_reviewed INTEGER NOT NULL DEFAULT 0,
                decision TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(shot_pack_id) REFERENCES shot_packs(id)
            );

            CREATE TABLE IF NOT EXISTS qc_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_pack_id INTEGER NOT NULL,
                decision TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                identity_score INTEGER NOT NULL,
                face_risk_score INTEGER NOT NULL,
                body_risk_score INTEGER NOT NULL,
                motion_score INTEGER NOT NULL,
                cultural_authenticity_score INTEGER NOT NULL,
                world_class_score INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(shot_pack_id) REFERENCES shot_packs(id)
            );

            CREATE TABLE IF NOT EXISTS connector_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 0,
                local_possible INTEGER NOT NULL DEFAULT 0,
                private_media_risk TEXT NOT NULL DEFAULT 'UNKNOWN',
                next_step TEXT NOT NULL DEFAULT 'UNKNOWN',
                raw_source TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reference_moodboards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                shot_pack_id TEXT NOT NULL DEFAULT '',
                composition_notes TEXT NOT NULL DEFAULT '',
                lighting_notes TEXT NOT NULL DEFAULT '',
                camera_notes TEXT NOT NULL DEFAULT '',
                color_notes TEXT NOT NULL DEFAULT '',
                cultural_notes TEXT NOT NULL DEFAULT '',
                rights_notes TEXT NOT NULL DEFAULT '',
                do_not_copy_warning TEXT NOT NULL DEFAULT 'URL/reference only. Do not copy or rehost copyrighted media.',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS generation_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_pack_id INTEGER NOT NULL,
                renderer TEXT NOT NULL,
                request_filename TEXT NOT NULL,
                spend_upload_limit TEXT NOT NULL,
                privacy_acknowledged INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'draft',
                package_path TEXT NOT NULL DEFAULT '',
                blocked_reasons TEXT NOT NULL DEFAULT '',
                dry_run_summary TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(shot_pack_id) REFERENCES shot_packs(id)
            );

            CREATE TABLE IF NOT EXISTS job_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'reference',
                policy_status TEXT NOT NULL DEFAULT 'unknown',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES generation_jobs(id)
            );

            CREATE TABLE IF NOT EXISTS job_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES generation_jobs(id)
            );

            CREATE TABLE IF NOT EXISTS job_outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                output_type TEXT NOT NULL,
                path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'dry_run',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES generation_jobs(id)
            );

            CREATE TABLE IF NOT EXISTS manual_exports (
                export_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                shot_id TEXT NOT NULL,
                renderer TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                export_folder TEXT NOT NULL,
                request_file TEXT NOT NULL,
                reference_manifest TEXT NOT NULL,
                qc_file TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(job_id) REFERENCES generation_jobs(id)
            );

            CREATE TABLE IF NOT EXISTS motion_references (
                motion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_id TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'local_path',
                source TEXT NOT NULL,
                source_title TEXT NOT NULL,
                owner_license TEXT NOT NULL,
                permitted_use TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                body_framing TEXT NOT NULL,
                travel_direction TEXT NOT NULL,
                speed TEXT NOT NULL,
                face_visibility TEXT NOT NULL,
                rights_status TEXT NOT NULL,
                source_owner_license TEXT NOT NULL,
                transfer_body_movement INTEGER NOT NULL DEFAULT 0,
                transfer_timing INTEGER NOT NULL DEFAULT 0,
                transfer_travel_path INTEGER NOT NULL DEFAULT 0,
                transfer_shoulder_torso_rhythm INTEGER NOT NULL DEFAULT 0,
                do_not_transfer_identity INTEGER NOT NULL DEFAULT 1,
                do_not_transfer_clothing INTEGER NOT NULL DEFAULT 1,
                do_not_transfer_location INTEGER NOT NULL DEFAULT 1,
                do_not_transfer_body_shape INTEGER NOT NULL DEFAULT 1,
                notes TEXT NOT NULL DEFAULT '',
                approval_status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS character_plates (
                plate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'character_start_frame',
                path TEXT NOT NULL,
                full_body_performer INTEGER NOT NULL DEFAULT 0,
                correct_deep_red_dress INTEGER NOT NULL DEFAULT 0,
                correct_bar_stage INTEGER NOT NULL DEFAULT 0,
                lateral_floor_space INTEGER NOT NULL DEFAULT 0,
                body_scale_matches_motion INTEGER NOT NULL DEFAULT 0,
                no_children INTEGER NOT NULL DEFAULT 0,
                approved_identity_state INTEGER NOT NULL DEFAULT 0,
                approval_status TEXT NOT NULL DEFAULT 'draft',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS imported_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                shot_id TEXT NOT NULL,
                job_id INTEGER NOT NULL,
                export_id INTEGER NOT NULL,
                renderer TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                file_size INTEGER NOT NULL DEFAULT 0,
                duration REAL NOT NULL DEFAULT 0,
                width INTEGER NOT NULL DEFAULT 0,
                height INTEGER NOT NULL DEFAULT 0,
                fps REAL NOT NULL DEFAULT 0,
                sha256 TEXT NOT NULL,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'imported',
                is_test INTEGER NOT NULL DEFAULT 0,
                codec TEXT NOT NULL DEFAULT '',
                poster_path TEXT NOT NULL DEFAULT '',
                contact_sheet_path TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(job_id) REFERENCES generation_jobs(id),
                FOREIGN KEY(export_id) REFERENCES manual_exports(export_id)
            );

            CREATE TABLE IF NOT EXISTS result_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id INTEGER NOT NULL,
                media_type TEXT NOT NULL,
                path TEXT NOT NULL,
                file_size INTEGER NOT NULL DEFAULT 0,
                sha256 TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(result_id) REFERENCES imported_results(result_id)
            );

            CREATE TABLE IF NOT EXISTS result_reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id INTEGER NOT NULL,
                identity_fidelity INTEGER NOT NULL,
                face_safety INTEGER NOT NULL,
                natural_body_proportions INTEGER NOT NULL,
                movement_realism INTEGER NOT NULL,
                choreography_fit INTEGER NOT NULL,
                dress_continuity INTEGER NOT NULL,
                bar_location_continuity INTEGER NOT NULL,
                burmese_cultural_authenticity INTEGER NOT NULL,
                camera_composition INTEGER NOT NULL,
                lighting INTEGER NOT NULL,
                hands_feet_limb_quality INTEGER NOT NULL,
                fabric_physics INTEGER NOT NULL,
                song_section_usefulness INTEGER NOT NULL,
                world_class_readiness INTEGER NOT NULL,
                no_kung_fu_martial_arts INTEGER NOT NULL DEFAULT 0,
                no_kpop_tiktok_drift INTEGER NOT NULL DEFAULT 0,
                no_karaoke_lounge_staging INTEGER NOT NULL DEFAULT 0,
                no_fake_lipsync INTEGER NOT NULL DEFAULT 0,
                no_microphone_centered INTEGER NOT NULL DEFAULT 0,
                no_fake_body_distortion INTEGER NOT NULL DEFAULT 0,
                no_wrong_dress INTEGER NOT NULL DEFAULT 0,
                no_wrong_venue INTEGER NOT NULL DEFAULT 0,
                no_dangerous_face_failure INTEGER NOT NULL DEFAULT 0,
                normal_speed_review_completed INTEGER NOT NULL DEFAULT 0,
                critical_failure INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(result_id) REFERENCES imported_results(result_id)
            );

            CREATE TABLE IF NOT EXISTS result_decisions (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id INTEGER NOT NULL,
                outcome TEXT NOT NULL,
                failure_tags TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                usable_time_range TEXT NOT NULL DEFAULT '',
                intended_song_section TEXT NOT NULL DEFAULT '',
                face_correction_requirement TEXT NOT NULL DEFAULT '',
                edit_notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(result_id) REFERENCES imported_results(result_id)
            );

            CREATE TABLE IF NOT EXISTS director_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea TEXT NOT NULL,
                project_path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'completed',
                output_path TEXT NOT NULL DEFAULT '',
                storyboard_count INTEGER NOT NULL DEFAULT 0,
                shot_count INTEGER NOT NULL DEFAULT 0,
                no_api_calls INTEGER NOT NULL DEFAULT 1,
                no_uploads INTEGER NOT NULL DEFAULT 1,
                no_generation INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS storyboard_cards (
                card_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL DEFAULT 0,
                shot_number TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                song_section TEXT NOT NULL DEFAULT '',
                timecode_start TEXT NOT NULL DEFAULT '',
                timecode_end TEXT NOT NULL DEFAULT '',
                purpose TEXT NOT NULL DEFAULT '',
                framing TEXT NOT NULL DEFAULT '',
                lens TEXT NOT NULL DEFAULT '',
                camera_movement TEXT NOT NULL DEFAULT '',
                lighting TEXT NOT NULL DEFAULT '',
                production_design TEXT NOT NULL DEFAULT '',
                performer_action TEXT NOT NULL DEFAULT '',
                exact_movement TEXT NOT NULL DEFAULT '',
                identity_risk TEXT NOT NULL DEFAULT '',
                body_motion_risk TEXT NOT NULL DEFAULT '',
                recommended_renderer TEXT NOT NULL DEFAULT '',
                fallback_renderer TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'planned',
                version INTEGER NOT NULL DEFAULT 1,
                frame_path TEXT NOT NULL DEFAULT '',
                raster_path TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS storyboard_decisions (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_number TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS storyboard_comments (
                comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_number TEXT NOT NULL,
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS previs_assets (
                asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_number TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                path TEXT NOT NULL,
                backend TEXT NOT NULL DEFAULT 'stdlib_png_composite',
                width INTEGER NOT NULL DEFAULT 0,
                height INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'created',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS motion_reference_analysis (
                analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
                motion_id INTEGER NOT NULL,
                shot_id TEXT NOT NULL,
                source TEXT NOT NULL,
                duration REAL NOT NULL DEFAULT 0,
                file_size INTEGER NOT NULL DEFAULT 0,
                analysis_status TEXT NOT NULL DEFAULT 'metadata_only',
                inferred_body_framing TEXT NOT NULL DEFAULT '',
                inferred_travel_direction TEXT NOT NULL DEFAULT '',
                warnings TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(motion_id) REFERENCES motion_references(motion_id)
            );

            CREATE TABLE IF NOT EXISTS burmese_caption_lines (
                line_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL,
                line_index INTEGER NOT NULL,
                original_text TEXT NOT NULL,
                normalized_unicode TEXT NOT NULL DEFAULT '',
                pronunciation_helper TEXT NOT NULL DEFAULT '',
                caption_text TEXT NOT NULL DEFAULT '',
                translation_note TEXT NOT NULL DEFAULT '',
                start_time TEXT NOT NULL DEFAULT '',
                end_time TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS lyric_source_lines (
                source_line_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL,
                line_index INTEGER NOT NULL,
                original_text TEXT NOT NULL,
                original_sha256 TEXT NOT NULL DEFAULT '',
                detected_encoding TEXT NOT NULL DEFAULT 'unknown',
                zawgyi_probability REAL NOT NULL DEFAULT 0,
                detection_confidence REAL NOT NULL DEFAULT 0,
                conversion_action TEXT NOT NULL DEFAULT 'preserve',
                unicode_text TEXT NOT NULL DEFAULT '',
                normalized_unicode TEXT NOT NULL DEFAULT '',
                conversion_uncertain INTEGER NOT NULL DEFAULT 0,
                is_section_label INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_path, line_index)
            );

            CREATE TABLE IF NOT EXISTS lyric_phrases (
                phrase_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_line_id INTEGER NOT NULL,
                phrase_index INTEGER NOT NULL,
                original_text TEXT NOT NULL,
                normalized_unicode TEXT NOT NULL DEFAULT '',
                pronunciation_helper TEXT NOT NULL DEFAULT '',
                caption_text TEXT NOT NULL DEFAULT '',
                start_time REAL NOT NULL DEFAULT 0,
                end_time REAL NOT NULL DEFAULT 0,
                timing_source TEXT NOT NULL DEFAULT '',
                alignment_confidence REAL NOT NULL DEFAULT 0,
                vocal_audio_path TEXT NOT NULL DEFAULT '',
                voice_audio_path TEXT NOT NULL DEFAULT '',
                voice_duration REAL NOT NULL DEFAULT 0,
                final_start_time REAL NOT NULL DEFAULT 0,
                final_end_time REAL NOT NULL DEFAULT 0,
                final_timing_source TEXT NOT NULL DEFAULT '',
                lipsync_timing_locked INTEGER NOT NULL DEFAULT 0,
                approval_state TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(source_line_id) REFERENCES lyric_source_lines(source_line_id)
            );

            CREATE TABLE IF NOT EXISTS lyric_syllable_markers (
                marker_id INTEGER PRIMARY KEY AUTOINCREMENT,
                phrase_id INTEGER NOT NULL,
                syllable_index INTEGER NOT NULL,
                syllable_text TEXT NOT NULL,
                relative_estimated_position REAL NOT NULL DEFAULT 0,
                alignment_status TEXT NOT NULL DEFAULT 'estimated_within_phrase',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(phrase_id) REFERENCES lyric_phrases(phrase_id)
            );

            CREATE TABLE IF NOT EXISTS voice_audio_assets (
                voice_asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                phrase_id INTEGER NOT NULL DEFAULT 0,
                source_path TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT 'manual_import',
                duration REAL NOT NULL DEFAULT 0,
                sample_rate INTEGER NOT NULL DEFAULT 0,
                channels INTEGER NOT NULL DEFAULT 0,
                sha256 TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'imported',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(phrase_id) REFERENCES lyric_phrases(phrase_id)
            );

            CREATE TABLE IF NOT EXISTS voice_phrase_alignments (
                alignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                phrase_id INTEGER NOT NULL,
                voice_asset_id INTEGER NOT NULL DEFAULT 0,
                start_time REAL NOT NULL DEFAULT 0,
                end_time REAL NOT NULL DEFAULT 0,
                duration REAL NOT NULL DEFAULT 0,
                alignment_source TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(phrase_id) REFERENCES lyric_phrases(phrase_id),
                FOREIGN KEY(voice_asset_id) REFERENCES voice_audio_assets(voice_asset_id)
            );

            CREATE TABLE IF NOT EXISTS pronunciation_overrides (
                override_id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_text TEXT NOT NULL,
                pronunciation_helper TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'approved',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS voice_tests (
                voice_test_id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                voice_name TEXT NOT NULL DEFAULT '',
                input_text TEXT NOT NULL,
                pronunciation_notes TEXT NOT NULL DEFAULT '',
                consent_confirmed INTEGER NOT NULL DEFAULT 0,
                cloud_upload_approved INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'planned',
                result_path TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS animatics (
                animatic_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL DEFAULT 0,
                path TEXT NOT NULL,
                frame_count INTEGER NOT NULL DEFAULT 0,
                duration REAL NOT NULL DEFAULT 0,
                backend TEXT NOT NULL DEFAULT 'html_timeline',
                status TEXT NOT NULL DEFAULT 'created',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS renderer_strategy_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_number TEXT NOT NULL,
                best_renderer TEXT NOT NULL,
                fallback_renderer TEXT NOT NULL,
                local_alternative TEXT NOT NULL DEFAULT '',
                required_inputs TEXT NOT NULL DEFAULT '',
                privacy_risk TEXT NOT NULL DEFAULT '',
                cost_risk TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'planned',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS research_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                rights_status TEXT NOT NULL DEFAULT 'link_only_do_not_copy',
                shot_pack_id TEXT NOT NULL DEFAULT '',
                verification_status TEXT NOT NULL DEFAULT 'search_suggestion_only',
                source_domain TEXT NOT NULL DEFAULT '',
                retrieval_date TEXT NOT NULL DEFAULT '',
                what_not_to_copy TEXT NOT NULL DEFAULT 'Do not copy or rehost copyrighted media.',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS autonomous_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea TEXT NOT NULL,
                project_path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                current_stage TEXT NOT NULL DEFAULT 'project_archaeology',
                active_provider TEXT NOT NULL DEFAULT '',
                provider_version TEXT NOT NULL DEFAULT '',
                output_dir TEXT NOT NULL DEFAULT '',
                blockers TEXT NOT NULL DEFAULT '[]',
                decisions_required TEXT NOT NULL DEFAULT '[]',
                superseded_by INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS autonomous_run_stages (
                stage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                stage_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                confidence REAL NOT NULL DEFAULT 0,
                provider TEXT NOT NULL DEFAULT '',
                provider_version TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                sources TEXT NOT NULL DEFAULT '[]',
                artifacts TEXT NOT NULL DEFAULT '[]',
                blockers TEXT NOT NULL DEFAULT '[]',
                started_at TEXT NOT NULL DEFAULT '',
                completed_at TEXT NOT NULL DEFAULT '',
                stdout_path TEXT NOT NULL DEFAULT '',
                stderr_path TEXT NOT NULL DEFAULT '',
                error TEXT NOT NULL DEFAULT '',
                UNIQUE(run_id, stage_name),
                FOREIGN KEY(run_id) REFERENCES autonomous_runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS autonomous_run_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                stage_name TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(run_id) REFERENCES autonomous_runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS visual_grammar (
                grammar_id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_number TEXT NOT NULL UNIQUE,
                composition TEXT NOT NULL DEFAULT '{}',
                camera TEXT NOT NULL DEFAULT '{}',
                lighting TEXT NOT NULL DEFAULT '{}',
                blocking TEXT NOT NULL DEFAULT '{}',
                diagram_path TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS local_backend_status (
                backend_id INTEGER PRIMARY KEY AUTOINCREMENT,
                backend_name TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                health TEXT NOT NULL DEFAULT '{}',
                blocker TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS setup_decisions (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_type TEXT NOT NULL,
                choice TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'recorded',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS local_capability_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                capability_type TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unknown',
                classification TEXT NOT NULL DEFAULT 'unavailable',
                details TEXT NOT NULL DEFAULT '{}',
                health TEXT NOT NULL DEFAULT '{}',
                last_checked TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(capability_type, name)
            );

            CREATE TABLE IF NOT EXISTS local_model_records (
                model_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT '',
                local_path TEXT NOT NULL DEFAULT '',
                version_or_commit TEXT NOT NULL DEFAULT '',
                code_license TEXT NOT NULL DEFAULT 'UNKNOWN',
                model_license TEXT NOT NULL DEFAULT 'UNKNOWN',
                commercial_use_state TEXT NOT NULL DEFAULT 'UNKNOWN',
                file_size INTEGER NOT NULL DEFAULT 0,
                model_family TEXT NOT NULL DEFAULT '',
                supported_tasks TEXT NOT NULL DEFAULT '',
                runtime TEXT NOT NULL DEFAULT '',
                health TEXT NOT NULL DEFAULT 'unknown',
                last_benchmark TEXT NOT NULL DEFAULT '',
                privacy TEXT NOT NULL DEFAULT 'local',
                approval_state TEXT NOT NULL DEFAULT 'not_approved',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS local_benchmarks (
                benchmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                runtime TEXT NOT NULL,
                hardware TEXT NOT NULL DEFAULT '',
                startup_time REAL NOT NULL DEFAULT 0,
                processing_time REAL NOT NULL DEFAULT 0,
                peak_memory TEXT NOT NULL DEFAULT '',
                dimensions TEXT NOT NULL DEFAULT '',
                result_path TEXT NOT NULL DEFAULT '',
                success INTEGER NOT NULL DEFAULT 0,
                quality_review_state TEXT NOT NULL DEFAULT 'not_reviewed',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS storyboard_model_installations (
                installation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                backend_id TEXT NOT NULL,
                selected_option TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'approval_recorded',
                approved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                approval_decision_id INTEGER NOT NULL DEFAULT 0,
                install_root TEXT NOT NULL DEFAULT '',
                pinned_commit TEXT NOT NULL DEFAULT '',
                commands_json TEXT NOT NULL DEFAULT '[]',
                downloaded_files_json TEXT NOT NULL DEFAULT '[]',
                uninstall_plan TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS storyboard_model_benchmarks (
                benchmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
                installation_id INTEGER NOT NULL DEFAULT 0,
                benchmark_type TEXT NOT NULL,
                model TEXT NOT NULL,
                runtime TEXT NOT NULL,
                prompt TEXT NOT NULL DEFAULT '',
                references_json TEXT NOT NULL DEFAULT '[]',
                seed INTEGER NOT NULL DEFAULT 0,
                width INTEGER NOT NULL DEFAULT 0,
                height INTEGER NOT NULL DEFAULT 0,
                startup_time REAL NOT NULL DEFAULT 0,
                generation_time REAL NOT NULL DEFAULT 0,
                memory TEXT NOT NULL DEFAULT '',
                output_path TEXT NOT NULL DEFAULT '',
                errors TEXT NOT NULL DEFAULT '',
                quality_review_state TEXT NOT NULL DEFAULT 'not_reviewed',
                origin_label TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(installation_id) REFERENCES storyboard_model_installations(installation_id)
            );

            CREATE TABLE IF NOT EXISTS storyboard_ai_variants (
                variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_number TEXT NOT NULL,
                source_card_version INTEGER NOT NULL DEFAULT 0,
                variant_type TEXT NOT NULL,
                backend_id TEXT NOT NULL,
                origin_label TEXT NOT NULL,
                prompt TEXT NOT NULL DEFAULT '',
                refinement_text TEXT NOT NULL DEFAULT '',
                seed INTEGER NOT NULL DEFAULT 0,
                width INTEGER NOT NULL DEFAULT 0,
                height INTEGER NOT NULL DEFAULT 0,
                image_path TEXT NOT NULL DEFAULT '',
                metadata_path TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'created',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS lipsync_jobs (
                job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL DEFAULT 0,
                shot_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'planned',
                provider TEXT NOT NULL DEFAULT 'manual_infinitetalk',
                mode TEXT NOT NULL DEFAULT 'video_to_video',
                eligibility TEXT NOT NULL DEFAULT '',
                source_video TEXT NOT NULL DEFAULT '',
                audio_segment_path TEXT NOT NULL DEFAULT '',
                full_mix_segment_path TEXT NOT NULL DEFAULT '',
                package_path TEXT NOT NULL DEFAULT '',
                blocked_reasons TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS lipsync_job_inputs (
                input_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                input_type TEXT NOT NULL,
                path TEXT NOT NULL,
                privacy_status TEXT NOT NULL DEFAULT 'unknown',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES lipsync_jobs(job_id)
            );

            CREATE TABLE IF NOT EXISTS lipsync_outputs (
                output_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                sha256 TEXT NOT NULL DEFAULT '',
                duration REAL NOT NULL DEFAULT 0,
                width INTEGER NOT NULL DEFAULT 0,
                height INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'imported',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES lipsync_jobs(job_id)
            );

            CREATE TABLE IF NOT EXISTS lipsync_reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                output_id INTEGER NOT NULL,
                sync_accuracy INTEGER NOT NULL DEFAULT 0,
                identity_consistency INTEGER NOT NULL DEFAULT 0,
                face_quality INTEGER NOT NULL DEFAULT 0,
                temporal_consistency INTEGER NOT NULL DEFAULT 0,
                expression_naturalness INTEGER NOT NULL DEFAULT 0,
                body_motion_naturalness INTEGER NOT NULL DEFAULT 0,
                background_preservation INTEGER NOT NULL DEFAULT 0,
                edit_usability INTEGER NOT NULL DEFAULT 0,
                critical_failures TEXT NOT NULL DEFAULT '',
                normal_speed_review_completed INTEGER NOT NULL DEFAULT 0,
                frame_level_review_completed INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(output_id) REFERENCES lipsync_outputs(output_id)
            );

            CREATE TABLE IF NOT EXISTS lipsync_decisions (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                output_id INTEGER NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                trim_recommendation TEXT NOT NULL DEFAULT '',
                face_correction_handoff TEXT NOT NULL DEFAULT '',
                edit_update_proposal TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(output_id) REFERENCES lipsync_outputs(output_id)
            );

            CREATE TABLE IF NOT EXISTS lipsync_provider_health (
                provider_id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL UNIQUE,
                classification TEXT NOT NULL DEFAULT 'unavailable',
                status TEXT NOT NULL DEFAULT 'not_configured',
                health TEXT NOT NULL DEFAULT '{}',
                last_checked TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS lipsync_audio_segments (
                segment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL DEFAULT 0,
                shot_id TEXT NOT NULL,
                source_audio TEXT NOT NULL,
                vocal_segment_path TEXT NOT NULL DEFAULT '',
                full_mix_segment_path TEXT NOT NULL DEFAULT '',
                lyrics_path TEXT NOT NULL DEFAULT '',
                pronunciation_path TEXT NOT NULL DEFAULT '',
                start_time REAL NOT NULL DEFAULT 0,
                end_time REAL NOT NULL DEFAULT 0,
                sample_rate INTEGER NOT NULL DEFAULT 44100,
                conversion_metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS studio_loops (
                loop_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_path TEXT NOT NULL,
                idea TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'understanding',
                current_iteration INTEGER NOT NULL DEFAULT 0,
                max_iterations INTEGER NOT NULL DEFAULT 5,
                quality_score REAL NOT NULL DEFAULT 0,
                acceptance_status TEXT NOT NULL DEFAULT 'not_evaluated',
                approval_required TEXT NOT NULL DEFAULT '',
                latest_artifact TEXT NOT NULL DEFAULT '',
                next_action TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS studio_loop_iterations (
                iteration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_id INTEGER NOT NULL,
                iteration_number INTEGER NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(loop_id) REFERENCES studio_loops(loop_id)
            );

            CREATE TABLE IF NOT EXISTS studio_loop_stages (
                stage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_id INTEGER NOT NULL,
                iteration_number INTEGER NOT NULL,
                stage_name TEXT NOT NULL,
                status TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT 'local',
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(loop_id) REFERENCES studio_loops(loop_id)
            );

            CREATE TABLE IF NOT EXISTS studio_loop_artifacts (
                artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_id INTEGER NOT NULL,
                iteration_number INTEGER NOT NULL,
                artifact_type TEXT NOT NULL,
                path TEXT NOT NULL,
                origin TEXT NOT NULL DEFAULT 'local',
                status TEXT NOT NULL DEFAULT 'created',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(loop_id) REFERENCES studio_loops(loop_id)
            );

            CREATE TABLE IF NOT EXISTS studio_loop_evaluations (
                evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_id INTEGER NOT NULL,
                iteration_number INTEGER NOT NULL,
                score REAL NOT NULL,
                status TEXT NOT NULL,
                path TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(loop_id) REFERENCES studio_loops(loop_id)
            );

            CREATE TABLE IF NOT EXISTS studio_loop_defects (
                defect_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_id INTEGER NOT NULL,
                iteration_number INTEGER NOT NULL,
                defect_code TEXT NOT NULL,
                severity TEXT NOT NULL,
                symptom TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                affected_artifact TEXT NOT NULL DEFAULT '',
                repair_status TEXT NOT NULL DEFAULT 'open',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(loop_id) REFERENCES studio_loops(loop_id)
            );

            CREATE TABLE IF NOT EXISTS studio_loop_repairs (
                repair_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_id INTEGER NOT NULL,
                iteration_number INTEGER NOT NULL,
                defect_code TEXT NOT NULL,
                repair_action TEXT NOT NULL,
                status TEXT NOT NULL,
                approval_required INTEGER NOT NULL DEFAULT 0,
                summary TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(loop_id) REFERENCES studio_loops(loop_id)
            );

            CREATE TABLE IF NOT EXISTS studio_loop_approvals (
                approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_id INTEGER NOT NULL,
                approval_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                decided_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(loop_id) REFERENCES studio_loops(loop_id)
            );

            CREATE TABLE IF NOT EXISTS studio_loop_costs (
                cost_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                estimated_cost TEXT NOT NULL DEFAULT '0',
                actual_cost TEXT NOT NULL DEFAULT '0',
                approval_id INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(loop_id) REFERENCES studio_loops(loop_id)
            );

            CREATE TABLE IF NOT EXISTS studio_loop_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(loop_id) REFERENCES studio_loops(loop_id)
            );

            CREATE TABLE IF NOT EXISTS studio_loop_final_reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                acceptance_status TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(loop_id) REFERENCES studio_loops(loop_id)
            );
            """
        )
        _add_column_if_missing(conn, "manual_exports", "approved_renderer", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "manual_exports", "maximum_generation_count", "INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing(conn, "manual_exports", "maximum_duration_seconds", "REAL NOT NULL DEFAULT 0")
        _add_column_if_missing(conn, "manual_exports", "maximum_credit_or_currency_spend", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "manual_exports", "exact_cloud_upload_approved", "INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing(conn, "manual_exports", "privacy_acknowledged", "INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing(conn, "manual_exports", "approval_timestamp", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "manual_exports", "readiness_status", "TEXT NOT NULL DEFAULT 'blocked'")
        _add_column_if_missing(conn, "manual_exports", "missing_requirements", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "research_items", "verification_status", "TEXT NOT NULL DEFAULT 'search_suggestion_only'")
        _add_column_if_missing(conn, "research_items", "source_domain", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "research_items", "retrieval_date", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "research_items", "what_not_to_copy", "TEXT NOT NULL DEFAULT 'Do not copy or rehost copyrighted media.'")
        _add_column_if_missing(conn, "lyric_source_lines", "source_category", "TEXT NOT NULL DEFAULT 'lyric'")
        _add_column_if_missing(conn, "lyric_source_lines", "conversion_engine", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "lyric_source_lines", "conversion_engine_version", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "lyric_source_lines", "conversion_status", "TEXT NOT NULL DEFAULT 'unreviewed'")
        _add_column_if_missing(conn, "lyric_source_lines", "validation_result", "TEXT NOT NULL DEFAULT 'unknown'")
        _add_column_if_missing(conn, "lyric_source_lines", "validation_warnings", "TEXT NOT NULL DEFAULT '[]'")
        _add_column_if_missing(conn, "lyric_source_lines", "converted_sha256", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "lyric_source_lines", "approved_unicode", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "lyric_source_lines", "user_corrected_unicode", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "lyric_source_lines", "review_status", "TEXT NOT NULL DEFAULT 'awaiting_review'")
        _add_column_if_missing(conn, "lyric_phrases", "approved_display_text", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "lyric_phrases", "display_status", "TEXT NOT NULL DEFAULT 'unavailable_for_production'")
        _add_column_if_missing(conn, "lyric_phrases", "timing_review_status", "TEXT NOT NULL DEFAULT 'accepted_from_local_boundary_analysis'")
        _add_column_if_missing(conn, "lyric_phrases", "listening_sync_status", "TEXT NOT NULL DEFAULT 'uncertain'")
        _add_column_if_missing(conn, "lyric_phrases", "listening_sync_notes", "TEXT NOT NULL DEFAULT ''")


def database_exists() -> bool:
    return Path(DATABASE_PATH).exists()


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
