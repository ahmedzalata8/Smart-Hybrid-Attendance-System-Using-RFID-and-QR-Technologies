--
-- PostgreSQL database dump
--

\restrict EiOuDg3EucsMLpWpuYGkSZv903Y24pURbLnK8jcLzZVieKteFVb9mLgEj98qffM

-- Dumped from database version 17.10
-- Dumped by pg_dump version 17.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP DATABASE IF EXISTS attendance_db;
--
-- Name: attendance_db; Type: DATABASE; Schema: -; Owner: -
--

CREATE DATABASE attendance_db WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'English_United States.1252';


\unrestrict EiOuDg3EucsMLpWpuYGkSZv903Y24pURbLnK8jcLzZVieKteFVb9mLgEj98qffM
\connect attendance_db
\restrict EiOuDg3EucsMLpWpuYGkSZv903Y24pURbLnK8jcLzZVieKteFVb9mLgEj98qffM

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: attendance_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.attendance_status AS ENUM (
    'present',
    'rejected',
    'revoked'
);


--
-- Name: session_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.session_status AS ENUM (
    'active',
    'closed'
);


--
-- Name: user_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.user_role AS ENUM (
    'student',
    'lecturer',
    'hod',
    'admin'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: attendance_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.attendance_records (
    session_id uuid NOT NULL,
    student_id uuid NOT NULL,
    seat_id uuid NOT NULL,
    status public.attendance_status NOT NULL,
    rejection_reason character varying(100),
    revocation_reason character varying(100),
    presence_pct integer,
    claimed_at timestamp with time zone NOT NULL,
    processed_at timestamp with time zone DEFAULT now() NOT NULL,
    finalized_at timestamp with time zone,
    id uuid NOT NULL
);


--
-- Name: attendance_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.attendance_sessions (
    course_id uuid NOT NULL,
    classroom_id uuid NOT NULL,
    lecturer_id uuid NOT NULL,
    status public.session_status NOT NULL,
    t_start timestamp with time zone NOT NULL,
    t_expiry timestamp with time zone NOT NULL,
    qr_token text NOT NULL,
    freshness_delta_sec integer NOT NULL,
    min_presence_pct integer NOT NULL,
    integrity_hash character varying(64),
    finalized_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    class_id uuid
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    session_id uuid NOT NULL,
    event_type character varying(50) NOT NULL,
    payload jsonb NOT NULL,
    integrity_hash character varying(64) NOT NULL,
    prev_hash character varying(64),
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: classrooms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.classrooms (
    name character varying(100) NOT NULL,
    department_id uuid NOT NULL,
    building character varying(100),
    floor integer,
    layout_rows integer NOT NULL,
    layout_cols integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: course_classes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.course_classes (
    course_id uuid NOT NULL,
    lecturer_id uuid NOT NULL,
    classroom_id uuid NOT NULL,
    day_of_week integer NOT NULL,
    start_time character varying(5) NOT NULL,
    end_time character varying(5) NOT NULL,
    group_name character varying(50),
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: COLUMN course_classes.day_of_week; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.course_classes.day_of_week IS '0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday';


--
-- Name: COLUMN course_classes.start_time; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.course_classes.start_time IS 'HH:MM format, e.g. 10:00';


--
-- Name: COLUMN course_classes.end_time; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.course_classes.end_time IS 'HH:MM format, e.g. 12:00';


--
-- Name: COLUMN course_classes.group_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.course_classes.group_name IS 'Optional section/group label, e.g. Group A, Section 1';


--
-- Name: courses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.courses (
    code character varying(20) NOT NULL,
    name character varying(200) NOT NULL,
    department_id uuid NOT NULL,
    lecturer_id uuid NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: departments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.departments (
    name character varying(150) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: enrollments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enrollments (
    student_id uuid NOT NULL,
    course_id uuid NOT NULL,
    enrolled_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL,
    class_id uuid
);


--
-- Name: rfid_readings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rfid_readings (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    tag_hex_id character varying(200) NOT NULL,
    tag_label character varying(50),
    seat_label character varying(20),
    angle_deg double precision,
    step_position integer,
    direction character varying(10),
    quadrant character varying(10),
    detected_at timestamp with time zone NOT NULL,
    received_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: scan_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scan_reports (
    session_id uuid NOT NULL,
    reader_device_id character varying(100) NOT NULL,
    tags_detected jsonb NOT NULL,
    scanned_at timestamp with time zone NOT NULL,
    received_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL
);


--
-- Name: seat_state_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.seat_state_history (
    session_id uuid NOT NULL,
    seat_id uuid NOT NULL,
    is_occupied boolean NOT NULL,
    detected_at timestamp with time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: seat_states; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.seat_states (
    session_id uuid NOT NULL,
    seat_id uuid NOT NULL,
    is_occupied boolean NOT NULL,
    last_seen_at timestamp with time zone,
    id uuid NOT NULL
);


--
-- Name: seats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.seats (
    classroom_id uuid NOT NULL,
    label character varying(20) NOT NULL,
    "row" integer NOT NULL,
    col integer NOT NULL,
    tag_id character varying(100) NOT NULL,
    id uuid NOT NULL,
    x_pct double precision,
    y_pct double precision
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(200) NOT NULL,
    role public.user_role NOT NULL,
    student_id character varying(50),
    department_id uuid NOT NULL,
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
a3b7c9d2e4f6
\.


--
-- Data for Name: attendance_records; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.attendance_records (session_id, student_id, seat_id, status, rejection_reason, revocation_reason, presence_pct, claimed_at, processed_at, finalized_at, id) FROM stdin;
6d9c1e2c-7fae-4dee-977f-fbceab85db08	8f3a62f9-14dd-4784-bb06-fa6c35c62c15	9d8236a3-a614-4c3f-a4dd-7341256c76e0	present	\N	\N	\N	2026-06-25 00:23:26.206896+03	2026-06-25 00:23:39.423933+03	\N	0bea1759-d982-41c2-9029-6474ebb28edb
\.


--
-- Data for Name: attendance_sessions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.attendance_sessions (course_id, classroom_id, lecturer_id, status, t_start, t_expiry, qr_token, freshness_delta_sec, min_presence_pct, integrity_hash, finalized_at, id, created_at, class_id) FROM stdin;
5a7d3605-4a3d-4b93-9ac8-fac3a35372c5	266cd434-c3c9-4711-a566-da1216cee64c	6eb805fb-6b6d-4bf6-b881-48c793bd9a73	closed	2026-06-18 18:20:41.585217+03	2026-06-18 19:20:41.585217+03	{"data": {"course_id": "5a7d3605-4a3d-4b93-9ac8-fac3a35372c5", "classroom_id": "266cd434-c3c9-4711-a566-da1216cee64c", "t_start": "2026-06-18T15:20:41.585217+00:00", "t_expiry": "2026-06-18T16:20:41.585217+00:00"}, "sig": "a35efc4b8934f1a4", "generated_at": "2026-06-18T15:20:41.593871+00:00"}	300	75	78645bc5977481152782d2da152999cff86d94747f952a9eea4aa6e6db3b20db	2026-06-18 18:20:42.276367+03	b225ad05-a70d-48cb-8c29-a31adc1077fc	2026-06-18 18:20:41.592096+03	\N
bb62eb74-4c8e-4126-b92b-e7081faa9141	266cd434-c3c9-4711-a566-da1216cee64c	26f03868-dfa5-4671-b970-d6ada84fabb7	closed	2026-06-18 18:44:09.722+03	2026-06-18 19:44:09.722+03	{"data": {"course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "classroom_id": "266cd434-c3c9-4711-a566-da1216cee64c", "t_start": "2026-06-18T15:44:09.722000+00:00", "t_expiry": "2026-06-18T16:44:09.722000+00:00"}, "sig": "a163b61ca96aef8f", "generated_at": "2026-06-18T15:44:09.735431+00:00"}	120	75	4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945	2026-06-18 19:44:16.092493+03	13018d36-164d-4bd1-b263-0ce8bd7fe964	2026-06-18 18:44:09.734243+03	\N
bb62eb74-4c8e-4126-b92b-e7081faa9141	266cd434-c3c9-4711-a566-da1216cee64c	26f03868-dfa5-4671-b970-d6ada84fabb7	closed	2026-06-23 16:31:42.251+03	2026-06-23 17:31:42.251+03	{"data": {"course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "classroom_id": "266cd434-c3c9-4711-a566-da1216cee64c", "t_start": "2026-06-23T13:31:42.251000+00:00", "t_expiry": "2026-06-23T14:31:42.251000+00:00"}, "sig": "29b0b352c6882b44", "generated_at": "2026-06-23T13:31:42.264830+00:00"}	120	75	4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945	2026-06-23 17:31:42.301185+03	131b85f5-42bf-4d8f-b39f-3b7883e79810	2026-06-23 16:31:42.262645+03	\N
bb62eb74-4c8e-4126-b92b-e7081faa9141	266cd434-c3c9-4711-a566-da1216cee64c	26f03868-dfa5-4671-b970-d6ada84fabb7	closed	2026-06-23 17:25:24.097+03	2026-06-23 18:25:24.097+03	{"data": {"course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "classroom_id": "266cd434-c3c9-4711-a566-da1216cee64c", "t_start": "2026-06-23T14:25:24.097000+00:00", "t_expiry": "2026-06-23T15:25:24.097000+00:00"}, "sig": "606e37aa36230ac8", "generated_at": "2026-06-23T14:25:24.110187+00:00"}	120	75	4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945	2026-06-23 18:25:49.316648+03	f14bdc3f-9822-43ab-9ef1-820f8f688526	2026-06-23 17:25:24.10917+03	\N
bb62eb74-4c8e-4126-b92b-e7081faa9141	266cd434-c3c9-4711-a566-da1216cee64c	26f03868-dfa5-4671-b970-d6ada84fabb7	closed	2026-06-23 18:28:09.969+03	2026-06-23 19:28:09.969+03	{"data": {"course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "classroom_id": "266cd434-c3c9-4711-a566-da1216cee64c", "t_start": "2026-06-23T15:28:09.969000+00:00", "t_expiry": "2026-06-23T16:28:09.969000+00:00"}, "sig": "8b1440c55abeb2d8", "generated_at": "2026-06-23T15:28:10.283363+00:00"}	120	75	4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945	2026-06-23 18:33:48.542042+03	3b39d291-5b3a-4a4a-b026-ef8e368a9a43	2026-06-23 18:28:10.282138+03	\N
bb62eb74-4c8e-4126-b92b-e7081faa9141	266cd434-c3c9-4711-a566-da1216cee64c	26f03868-dfa5-4671-b970-d6ada84fabb7	closed	2026-06-23 18:33:53.168+03	2026-06-23 19:33:53.168+03	{"data": {"course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "classroom_id": "266cd434-c3c9-4711-a566-da1216cee64c", "t_start": "2026-06-23T15:33:53.168000+00:00", "t_expiry": "2026-06-23T16:33:53.168000+00:00"}, "sig": "346549f3ee617e03", "generated_at": "2026-06-23T15:33:53.181186+00:00"}	120	75	4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945	2026-06-23 19:33:54.349835+03	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	2026-06-23 18:33:53.180796+03	\N
bb62eb74-4c8e-4126-b92b-e7081faa9141	266cd434-c3c9-4711-a566-da1216cee64c	26f03868-dfa5-4671-b970-d6ada84fabb7	closed	2026-06-24 15:31:25.281+03	2026-06-24 16:31:25.281+03	{"data": {"course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "classroom_id": "266cd434-c3c9-4711-a566-da1216cee64c", "t_start": "2026-06-24T12:31:25.281000+00:00", "t_expiry": "2026-06-24T13:31:25.281000+00:00"}, "sig": "fc995ef349c73288", "generated_at": "2026-06-24T12:31:25.294597+00:00"}	120	75	4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945	2026-06-24 17:36:56.805182+03	06da16db-4386-4acf-9f17-847f80f1ee45	2026-06-24 15:31:25.292589+03	\N
bb62eb74-4c8e-4126-b92b-e7081faa9141	266cd434-c3c9-4711-a566-da1216cee64c	26f03868-dfa5-4671-b970-d6ada84fabb7	closed	2026-06-24 17:37:04.504+03	2026-06-24 18:37:04.504+03	{"data": {"course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "classroom_id": "266cd434-c3c9-4711-a566-da1216cee64c", "t_start": "2026-06-24T14:37:04.504000+00:00", "t_expiry": "2026-06-24T15:37:04.504000+00:00"}, "sig": "0140217a801d3cc0", "generated_at": "2026-06-24T14:37:04.820739+00:00"}	120	75	4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945	2026-06-24 18:37:26.684584+03	371585a8-73c5-4a79-883f-94f891ad2316	2026-06-24 17:37:04.819029+03	\N
bb62eb74-4c8e-4126-b92b-e7081faa9141	266cd434-c3c9-4711-a566-da1216cee64c	26f03868-dfa5-4671-b970-d6ada84fabb7	closed	2026-06-24 20:14:26.795+03	2026-06-24 21:14:26.795+03	{"data": {"course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "classroom_id": "266cd434-c3c9-4711-a566-da1216cee64c", "t_start": "2026-06-24T17:14:26.795000+00:00", "t_expiry": "2026-06-24T18:14:26.795000+00:00"}, "sig": "a8b5dd4c7923cbfa", "generated_at": "2026-06-24T17:14:27.115734+00:00"}	120	75	4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945	2026-06-24 21:16:22.141922+03	2511620d-16e1-4b06-acf3-664b7ebbce4c	2026-06-24 20:14:27.113463+03	\N
bb62eb74-4c8e-4126-b92b-e7081faa9141	266cd434-c3c9-4711-a566-da1216cee64c	26f03868-dfa5-4671-b970-d6ada84fabb7	closed	2026-06-24 21:16:34.599+03	2026-06-24 22:16:34.599+03	{"data": {"course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "classroom_id": "266cd434-c3c9-4711-a566-da1216cee64c", "t_start": "2026-06-24T18:16:34.599000+00:00", "t_expiry": "2026-06-24T19:16:34.599000+00:00"}, "sig": "91bbb358c5d49099", "generated_at": "2026-06-24T18:16:34.922964+00:00"}	120	75	4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945	2026-06-24 21:53:08.438702+03	9417ec99-b463-4cd1-b726-e7b31f2e0407	2026-06-24 21:16:34.921051+03	\N
bb62eb74-4c8e-4126-b92b-e7081faa9141	266cd434-c3c9-4711-a566-da1216cee64c	26f03868-dfa5-4671-b970-d6ada84fabb7	closed	2026-06-24 21:53:13.334+03	2026-06-24 22:53:13.334+03	{"data": {"course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "classroom_id": "266cd434-c3c9-4711-a566-da1216cee64c", "t_start": "2026-06-24T18:53:13.334000+00:00", "t_expiry": "2026-06-24T19:53:13.334000+00:00"}, "sig": "e63da1e9c9a17b36", "generated_at": "2026-06-24T18:53:13.658417+00:00"}	120	75	4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945	2026-06-24 21:54:53.048043+03	01cf57e1-f1ae-45bd-b406-0679391273f1	2026-06-24 21:53:13.656846+03	\N
bb62eb74-4c8e-4126-b92b-e7081faa9141	266cd434-c3c9-4711-a566-da1216cee64c	26f03868-dfa5-4671-b970-d6ada84fabb7	closed	2026-06-24 21:55:02.906+03	2026-06-24 22:55:02.906+03	{"data": {"course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "classroom_id": "266cd434-c3c9-4711-a566-da1216cee64c", "t_start": "2026-06-24T18:55:02.906000+00:00", "t_expiry": "2026-06-24T19:55:02.906000+00:00"}, "sig": "e8e06eb589a35377", "generated_at": "2026-06-24T18:55:03.218676+00:00"}	120	75	4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945	2026-06-24 22:55:21.221725+03	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	2026-06-24 21:55:03.218708+03	\N
bb62eb74-4c8e-4126-b92b-e7081faa9141	266cd434-c3c9-4711-a566-da1216cee64c	26f03868-dfa5-4671-b970-d6ada84fabb7	active	2026-06-24 23:03:34.563+03	2026-06-25 02:03:34.563+03	{"data": {"course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "classroom_id": "266cd434-c3c9-4711-a566-da1216cee64c", "t_start": "2026-06-24T20:03:34.563000+00:00", "t_expiry": "2026-06-24T23:03:34.563000+00:00"}, "sig": "1fbce23047db4930", "generated_at": "2026-06-24T20:03:34.888806+00:00"}	120	75	\N	\N	6d9c1e2c-7fae-4dee-977f-fbceab85db08	2026-06-24 23:03:34.8878+03	\N
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.audit_logs (session_id, event_type, payload, integrity_hash, prev_hash, id, created_at) FROM stdin;
b225ad05-a70d-48cb-8c29-a31adc1077fc	session_finalized	{"present": 0, "revoked": 1, "rejected": 1, "course_id": "5a7d3605-4a3d-4b93-9ac8-fac3a35372c5", "session_id": "b225ad05-a70d-48cb-8c29-a31adc1077fc", "total_records": 2, "integrity_hash": "78645bc5977481152782d2da152999cff86d94747f952a9eea4aa6e6db3b20db"}	e9e0714c28684f8dec9b819ce3460f5abeb977ff2341573df48f959c1fb87db4	\N	0be978e5-4409-45d1-b70e-ffe12550e433	2026-06-18 18:20:42.275834+03
13018d36-164d-4bd1-b263-0ce8bd7fe964	session_finalized	{"present": 0, "revoked": 0, "rejected": 0, "course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "session_id": "13018d36-164d-4bd1-b263-0ce8bd7fe964", "total_records": 0, "integrity_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"}	16589de1555e0b60f9bad2cb0411760a6ca8fed37bc70ff9554bf8403c50228b	e9e0714c28684f8dec9b819ce3460f5abeb977ff2341573df48f959c1fb87db4	aee547fb-1e5b-449c-8090-1f554bed60ff	2026-06-18 19:44:16.092427+03
131b85f5-42bf-4d8f-b39f-3b7883e79810	session_finalized	{"present": 0, "revoked": 0, "rejected": 0, "course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "session_id": "131b85f5-42bf-4d8f-b39f-3b7883e79810", "total_records": 0, "integrity_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"}	937599e1611679430ff01ab5fe2945c41c0d856731da2841a1ffd39d9ca1d34b	16589de1555e0b60f9bad2cb0411760a6ca8fed37bc70ff9554bf8403c50228b	ce563dd9-1118-4683-976d-6736ec71452e	2026-06-23 17:31:42.300869+03
f14bdc3f-9822-43ab-9ef1-820f8f688526	session_finalized	{"present": 0, "revoked": 0, "rejected": 0, "course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "session_id": "f14bdc3f-9822-43ab-9ef1-820f8f688526", "total_records": 0, "integrity_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"}	23b205631f4c831a9832dffe14c4d8489d1776d38cc065156f2e514ca54a48dc	937599e1611679430ff01ab5fe2945c41c0d856731da2841a1ffd39d9ca1d34b	5cccd388-784c-46b7-a0bf-a19f99478977	2026-06-23 18:25:49.316357+03
3b39d291-5b3a-4a4a-b026-ef8e368a9a43	session_finalized	{"present": 0, "revoked": 0, "rejected": 0, "course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "session_id": "3b39d291-5b3a-4a4a-b026-ef8e368a9a43", "total_records": 0, "integrity_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"}	0753044b82d9423b00f8c800e3dd6905c5d38b89f0290e24c4c87e49285ab249	23b205631f4c831a9832dffe14c4d8489d1776d38cc065156f2e514ca54a48dc	de3f7993-fac2-41da-970a-ab404159bc96	2026-06-23 18:33:48.541605+03
e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	session_finalized	{"present": 0, "revoked": 0, "rejected": 0, "course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "session_id": "e2dc5bf0-db01-4ce2-969f-144ab1a5a45a", "total_records": 0, "integrity_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"}	ed9cff3f4d1cfcff3270d09fd2b8cb656afc12d41b3914fee4f961ae48600499	0753044b82d9423b00f8c800e3dd6905c5d38b89f0290e24c4c87e49285ab249	2fa37938-9e0d-4632-adcc-02540f59f166	2026-06-23 19:33:54.34958+03
06da16db-4386-4acf-9f17-847f80f1ee45	session_finalized	{"present": 0, "revoked": 0, "rejected": 0, "course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "session_id": "06da16db-4386-4acf-9f17-847f80f1ee45", "total_records": 0, "integrity_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"}	97df914e5b3e149e584eee82d2932569e3eae64d16fc51d27cf930ef3a21530b	ed9cff3f4d1cfcff3270d09fd2b8cb656afc12d41b3914fee4f961ae48600499	4a59f4f5-c8e6-49c8-9ed3-4d3d5213ee39	2026-06-24 17:36:56.786618+03
371585a8-73c5-4a79-883f-94f891ad2316	session_finalized	{"present": 0, "revoked": 0, "rejected": 0, "course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "session_id": "371585a8-73c5-4a79-883f-94f891ad2316", "total_records": 0, "integrity_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"}	36ec421264c114818d9bdc31d55cbca2b9ec151aac29e86849611f53a738bb78	97df914e5b3e149e584eee82d2932569e3eae64d16fc51d27cf930ef3a21530b	eed46b2b-4f3f-4a8e-af2a-7c746260a81c	2026-06-24 18:37:26.684317+03
2511620d-16e1-4b06-acf3-664b7ebbce4c	session_finalized	{"present": 0, "revoked": 0, "rejected": 0, "course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "session_id": "2511620d-16e1-4b06-acf3-664b7ebbce4c", "total_records": 0, "integrity_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"}	6ea4c58cb1eb4fb06ede19d37dcd106876df54719bb128691c25ef68e6bfd69a	36ec421264c114818d9bdc31d55cbca2b9ec151aac29e86849611f53a738bb78	d4ab3911-6c05-4380-8684-2b54415f5549	2026-06-24 21:16:22.134658+03
9417ec99-b463-4cd1-b726-e7b31f2e0407	session_finalized	{"present": 0, "revoked": 0, "rejected": 0, "course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "session_id": "9417ec99-b463-4cd1-b726-e7b31f2e0407", "total_records": 0, "integrity_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"}	cdde564429e31e5d7bd376e892d35c4b404f97ca06205c8543e76d173c438553	6ea4c58cb1eb4fb06ede19d37dcd106876df54719bb128691c25ef68e6bfd69a	49468543-dd12-49d7-85f3-ab267b97c81c	2026-06-24 21:53:08.438222+03
01cf57e1-f1ae-45bd-b406-0679391273f1	session_finalized	{"present": 0, "revoked": 0, "rejected": 0, "course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "session_id": "01cf57e1-f1ae-45bd-b406-0679391273f1", "total_records": 0, "integrity_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"}	52ce5154b87972b086bf5f5fa7c7902adeade593d87f36c3776fc854f40190d8	cdde564429e31e5d7bd376e892d35c4b404f97ca06205c8543e76d173c438553	55ac1174-fbb1-4ca4-8b52-acf20f9d39af	2026-06-24 21:54:53.047531+03
bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	session_finalized	{"present": 0, "revoked": 0, "rejected": 0, "course_id": "bb62eb74-4c8e-4126-b92b-e7081faa9141", "session_id": "bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e", "total_records": 0, "integrity_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"}	f44bdb4478baf849d98bbcb27af12c0995174b0cab7cbd28c0b4a1e0443a2537	52ce5154b87972b086bf5f5fa7c7902adeade593d87f36c3776fc854f40190d8	be1da809-f7ea-4de4-9106-500d90dfb321	2026-06-24 22:55:21.221493+03
\.


--
-- Data for Name: classrooms; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.classrooms (name, department_id, building, floor, layout_rows, layout_cols, id, created_at) FROM stdin;
Room 101	b1be98cb-4ab8-48a1-b304-294823ded71f	\N	\N	3	4	266cd434-c3c9-4711-a566-da1216cee64c	2026-06-18 18:20:40.565727+03
\.


--
-- Data for Name: course_classes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.course_classes (course_id, lecturer_id, classroom_id, day_of_week, start_time, end_time, group_name, id, created_at) FROM stdin;
bb62eb74-4c8e-4126-b92b-e7081faa9141	26f03868-dfa5-4671-b970-d6ada84fabb7	266cd434-c3c9-4711-a566-da1216cee64c	2	08:00	10:00		eb2e748d-8037-406b-bcd8-4be7157b42fd	2026-06-18 18:42:58.426842+03
bb62eb74-4c8e-4126-b92b-e7081faa9141	26f03868-dfa5-4671-b970-d6ada84fabb7	266cd434-c3c9-4711-a566-da1216cee64c	1	07:00	18:00		dc9b80b5-bae2-4a26-a96b-94f0e1547a0a	2026-06-24 15:24:18.634105+03
\.


--
-- Data for Name: courses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.courses (code, name, department_id, lecturer_id, id, created_at) FROM stdin;
CS301	Software Engineering	b1be98cb-4ab8-48a1-b304-294823ded71f	6eb805fb-6b6d-4bf6-b881-48c793bd9a73	5a7d3605-4a3d-4b93-9ac8-fac3a35372c5	2026-06-18 18:20:41.572314+03
CY301	DSS	b1be98cb-4ab8-48a1-b304-294823ded71f	26f03868-dfa5-4671-b970-d6ada84fabb7	bb62eb74-4c8e-4126-b92b-e7081faa9141	2026-06-18 18:42:44.648056+03
\.


--
-- Data for Name: departments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.departments (name, id, created_at) FROM stdin;
Computer Science	b1be98cb-4ab8-48a1-b304-294823ded71f	2026-06-18 18:20:40.565727+03
\.


--
-- Data for Name: enrollments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.enrollments (student_id, course_id, enrolled_at, id, class_id) FROM stdin;
41086536-3c6e-4553-9740-46b671b935b4	5a7d3605-4a3d-4b93-9ac8-fac3a35372c5	2026-06-18 18:20:41.572314+03	84594b1b-118d-4152-9713-0ceec7c276da	\N
fb9d07e7-5789-4dad-bb75-18e203a9bad5	5a7d3605-4a3d-4b93-9ac8-fac3a35372c5	2026-06-18 18:20:41.572314+03	691b6ef7-062b-4584-9cd0-425c2a780aea	\N
fb9d07e7-5789-4dad-bb75-18e203a9bad5	5a7d3605-4a3d-4b93-9ac8-fac3a35372c5	2026-06-18 18:43:50.970163+03	ada958da-a2f4-4543-aff6-fdf6c543ebf9	\N
8f3a62f9-14dd-4784-bb06-fa6c35c62c15	bb62eb74-4c8e-4126-b92b-e7081faa9141	2026-06-24 15:28:25.999339+03	7d57100a-55a0-423d-9ab0-b8678809c172	dc9b80b5-bae2-4a26-a96b-94f0e1547a0a
8f3a62f9-14dd-4784-bb06-fa6c35c62c15	bb62eb74-4c8e-4126-b92b-e7081faa9141	2026-06-24 15:28:43.637131+03	50a43246-a57b-41c0-a241-543aba01245d	eb2e748d-8037-406b-bcd8-4be7157b42fd
7976e276-0253-4563-b8ef-bb4be261bf73	bb62eb74-4c8e-4126-b92b-e7081faa9141	2026-06-24 15:28:52.592881+03	8d3a9fa0-dba5-4212-8cfe-401bcc3af76a	dc9b80b5-bae2-4a26-a96b-94f0e1547a0a
7976e276-0253-4563-b8ef-bb4be261bf73	bb62eb74-4c8e-4126-b92b-e7081faa9141	2026-06-24 15:29:06.775156+03	34da5d7d-7922-45c5-b02a-a37222554788	eb2e748d-8037-406b-bcd8-4be7157b42fd
ac340fc3-0e9f-437f-8281-3968fa0476b3	bb62eb74-4c8e-4126-b92b-e7081faa9141	2026-06-24 15:29:14.068386+03	e52ef463-e441-4482-8f93-f95a4222af1c	dc9b80b5-bae2-4a26-a96b-94f0e1547a0a
ac340fc3-0e9f-437f-8281-3968fa0476b3	bb62eb74-4c8e-4126-b92b-e7081faa9141	2026-06-24 15:29:19.277756+03	849dc820-88d7-45fb-8ee3-2fed77cdad7c	eb2e748d-8037-406b-bcd8-4be7157b42fd
0232cb03-a5d3-415f-9df9-755e10ee5477	bb62eb74-4c8e-4126-b92b-e7081faa9141	2026-06-24 15:29:30.608335+03	d5772814-d3d3-4988-be7c-affbc072db3c	dc9b80b5-bae2-4a26-a96b-94f0e1547a0a
0232cb03-a5d3-415f-9df9-755e10ee5477	bb62eb74-4c8e-4126-b92b-e7081faa9141	2026-06-24 15:29:36.039569+03	e9c977e9-e67c-41d3-a979-5fcdb32c3405	eb2e748d-8037-406b-bcd8-4be7157b42fd
323aa6dd-da2b-4cbe-8f43-cb5cf05d7e7f	bb62eb74-4c8e-4126-b92b-e7081faa9141	2026-06-24 15:29:43.858348+03	80ad1ab6-c756-4c36-9715-2de8803f6cea	eb2e748d-8037-406b-bcd8-4be7157b42fd
323aa6dd-da2b-4cbe-8f43-cb5cf05d7e7f	bb62eb74-4c8e-4126-b92b-e7081faa9141	2026-06-24 15:29:53.899439+03	2a425f7a-a031-43a1-91a7-bddddc22bdc1	dc9b80b5-bae2-4a26-a96b-94f0e1547a0a
\.


--
-- Data for Name: rfid_readings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.rfid_readings (id, session_id, tag_hex_id, tag_label, seat_label, angle_deg, step_position, direction, quadrant, detected_at, received_at) FROM stdin;
1251a926-c3e4-4f57-9084-76e34a0c7779	131b85f5-42bf-4d8f-b39f-3b7883e79810	181E181E1E98E698F8181E0698780618981E98801E	Unknown-4	Unknown-4	112.5	635	CW	Q2	2026-06-23 16:54:52.915886+03	2026-06-23 16:55:15.783893+03
db72242d-b93f-491d-8327-5750d99c8122	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	112.5	635	CW	Q2	2026-06-23 16:54:53.118831+03	2026-06-23 16:55:15.783893+03
890d2413-bb0c-40db-b3d0-1786d9a662a7	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E698F8981E98801E	Unknown-5	Unknown-5	135	762	CW	Q2	2026-06-23 16:54:53.200409+03	2026-06-23 16:55:15.783893+03
8fa3630c-f8bc-47e1-92e6-f635301dd4a4	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	135	762	CW	Q2	2026-06-23 16:54:53.261519+03	2026-06-23 16:55:15.783893+03
fd885f11-159c-4aea-b9b7-b27aa7aabab4	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66181898F8987860981E98801E	Unknown-6	Unknown-6	135	762	CW	Q2	2026-06-23 16:54:53.343252+03	2026-06-23 16:55:15.783893+03
75835ecf-e12a-4aea-b538-38c7a14ec77f	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E18981E98801E	Unknown-3	Unknown-3	135	762	CW	Q2	2026-06-23 16:54:53.424569+03	2026-06-23 16:55:15.783893+03
003b5ea2-6cf4-47b1-a226-6d645aac2f70	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E1E981E98801E	Unknown-3	Unknown-3	157.5	889	CW	Q2	2026-06-23 16:54:53.485592+03	2026-06-23 16:55:15.783893+03
1e0205d5-032c-45ca-894f-0ba4a183a3fa	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	157.5	889	CW	Q2	2026-06-23 16:54:53.566942+03	2026-06-23 16:55:15.783893+03
9f0b9bb7-34f7-4944-b674-75bb37452228	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	157.5	889	CW	Q2	2026-06-23 16:54:53.648721+03	2026-06-23 16:55:15.783893+03
0ebeffaa-1623-477c-9e34-1ace81457c47	131b85f5-42bf-4d8f-b39f-3b7883e79810	181E181E1E98E698F8181E0698780618981E98801E	Unknown-4	Unknown-4	112.5	635	CW	Q2	2026-06-23 16:54:52.915886+03	2026-06-23 16:55:16.602516+03
d2833d1e-7d76-436b-ae39-3e6fb2854c86	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	112.5	635	CW	Q2	2026-06-23 16:54:53.118831+03	2026-06-23 16:55:16.602516+03
0064dedd-a3be-4c85-aea9-5e65d90c97d7	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E698F8981E98801E	Unknown-5	Unknown-5	135	762	CW	Q2	2026-06-23 16:54:53.200409+03	2026-06-23 16:55:16.602516+03
4e547596-3ec5-4e3a-95f8-e70f5bb5f0c4	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	135	762	CW	Q2	2026-06-23 16:54:53.261519+03	2026-06-23 16:55:16.602516+03
05812af5-4fb4-4d5f-b356-d147060feb9e	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66181898F8987860981E98801E	Unknown-6	Unknown-6	135	762	CW	Q2	2026-06-23 16:54:53.343252+03	2026-06-23 16:55:16.602516+03
8fe3b006-124d-4491-aa35-cc8c26c665b9	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E18981E98801E	Unknown-3	Unknown-3	135	762	CW	Q2	2026-06-23 16:54:53.424569+03	2026-06-23 16:55:16.602516+03
d20f5492-95f8-4a73-b596-c9b044026840	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E1E981E98801E	Unknown-3	Unknown-3	157.5	889	CW	Q2	2026-06-23 16:54:53.485592+03	2026-06-23 16:55:16.602516+03
a95c6600-1293-4a33-9362-a610241ccb9d	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	157.5	889	CW	Q2	2026-06-23 16:54:53.566942+03	2026-06-23 16:55:16.602516+03
c60e2994-44c3-4b80-b845-49e9ac95d2a4	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	157.5	889	CW	Q2	2026-06-23 16:54:53.648721+03	2026-06-23 16:55:16.602516+03
8f62c2cb-af94-42f5-81d2-190a37645b94	131b85f5-42bf-4d8f-b39f-3b7883e79810	181E181E1E98E698F8181E0698780618981E98801E	Unknown-4	Unknown-4	112.5	635	CW	Q2	2026-06-23 16:54:52.915886+03	2026-06-23 16:55:17.249559+03
5ed3a7aa-1069-491e-95eb-1227ef601546	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	112.5	635	CW	Q2	2026-06-23 16:54:53.118831+03	2026-06-23 16:55:17.249559+03
593c1dac-3dfc-4cb2-b1b3-093f927339e0	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E698F8981E98801E	Unknown-5	Unknown-5	135	762	CW	Q2	2026-06-23 16:54:53.200409+03	2026-06-23 16:55:17.249559+03
4f354e47-ddf5-4e1f-94c5-eb7552bf03f7	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	135	762	CW	Q2	2026-06-23 16:54:53.261519+03	2026-06-23 16:55:17.249559+03
11729153-b265-4eb8-b5ff-2923da525319	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66181898F8987860981E98801E	Unknown-6	Unknown-6	135	762	CW	Q2	2026-06-23 16:54:53.343252+03	2026-06-23 16:55:17.249559+03
43d743e2-eaad-405f-93dd-8398cd4e9d9d	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E18981E98801E	Unknown-3	Unknown-3	135	762	CW	Q2	2026-06-23 16:54:53.424569+03	2026-06-23 16:55:17.249559+03
3ba011bb-436b-4858-8a2a-e4fa452b7eb6	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E1E981E98801E	Unknown-3	Unknown-3	157.5	889	CW	Q2	2026-06-23 16:54:53.485592+03	2026-06-23 16:55:17.249559+03
e525724b-40df-46e5-a656-a512c6794b25	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	157.5	889	CW	Q2	2026-06-23 16:54:53.566942+03	2026-06-23 16:55:17.249559+03
d0dd2f28-f7da-4769-946d-45654c8bcc07	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	157.5	889	CW	Q2	2026-06-23 16:54:53.648721+03	2026-06-23 16:55:17.249559+03
60a63010-5fec-4e28-a30a-3920a836570c	131b85f5-42bf-4d8f-b39f-3b7883e79810	181E181E1E98E698F8181E0698780618981E98801E	Unknown-4	Unknown-4	112.5	635	CW	Q2	2026-06-23 16:54:52.915886+03	2026-06-23 16:55:17.401484+03
7bebc1b5-4caa-46c3-8ef5-352feedc6bae	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	112.5	635	CW	Q2	2026-06-23 16:54:53.118831+03	2026-06-23 16:55:17.401484+03
6ee3a4bb-4725-40e3-9dc1-52c6d2fd90a1	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E698F8981E98801E	Unknown-5	Unknown-5	135	762	CW	Q2	2026-06-23 16:54:53.200409+03	2026-06-23 16:55:17.401484+03
4d153459-1038-4600-ae3c-00f038f243f9	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	135	762	CW	Q2	2026-06-23 16:54:53.261519+03	2026-06-23 16:55:17.401484+03
efc90dc2-e0b7-4369-a2ed-a8c48c70056e	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66181898F8987860981E98801E	Unknown-6	Unknown-6	135	762	CW	Q2	2026-06-23 16:54:53.343252+03	2026-06-23 16:55:17.401484+03
a8600008-cb8c-43f2-a073-90fb1094d6e5	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E18981E98801E	Unknown-3	Unknown-3	135	762	CW	Q2	2026-06-23 16:54:53.424569+03	2026-06-23 16:55:17.401484+03
9e016059-cb54-4309-9eb3-1483c00b73ae	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E1E981E98801E	Unknown-3	Unknown-3	157.5	889	CW	Q2	2026-06-23 16:54:53.485592+03	2026-06-23 16:55:17.401484+03
c42eeeef-3dad-4337-9b60-0c846e6f3ffd	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	157.5	889	CW	Q2	2026-06-23 16:54:53.566942+03	2026-06-23 16:55:17.401484+03
51de6ea8-239c-4671-937b-15e14f6e7113	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	157.5	889	CW	Q2	2026-06-23 16:54:53.648721+03	2026-06-23 16:55:17.401484+03
9e5d0586-4a80-47fb-8d6d-4ca7ad447b5e	131b85f5-42bf-4d8f-b39f-3b7883e79810	181E181E1E98E698F8181E0698780618981E98801E	Unknown-4	Unknown-4	112.5	635	CW	Q2	2026-06-23 16:54:52.915886+03	2026-06-23 16:55:17.537191+03
0c4debe7-661d-4d0d-a70b-2b939c07498f	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	112.5	635	CW	Q2	2026-06-23 16:54:53.118831+03	2026-06-23 16:55:17.537191+03
8d63e006-5e62-4e88-b6bb-5d7a7ad3829a	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E698F8981E98801E	Unknown-5	Unknown-5	135	762	CW	Q2	2026-06-23 16:54:53.200409+03	2026-06-23 16:55:17.537191+03
fe38849a-d578-4e26-965b-9947ae287804	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	135	762	CW	Q2	2026-06-23 16:54:53.261519+03	2026-06-23 16:55:17.537191+03
f1cf3cd8-5dbd-4d73-bf84-5be8b582bb81	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66181898F8987860981E98801E	Unknown-6	Unknown-6	135	762	CW	Q2	2026-06-23 16:54:53.343252+03	2026-06-23 16:55:17.537191+03
16f67d72-f2b8-455f-bc04-1fbd65e4217b	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E18981E98801E	Unknown-3	Unknown-3	135	762	CW	Q2	2026-06-23 16:54:53.424569+03	2026-06-23 16:55:17.537191+03
c56aa677-b29f-4ff9-a62b-ab21b27dfa26	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E1E981E98801E	Unknown-3	Unknown-3	157.5	889	CW	Q2	2026-06-23 16:54:53.485592+03	2026-06-23 16:55:17.537191+03
d151f7f8-d5f2-4d67-a086-ebad513ed12e	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	157.5	889	CW	Q2	2026-06-23 16:54:53.566942+03	2026-06-23 16:55:17.537191+03
c1495b31-543f-4b92-bc28-a115343f6286	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	157.5	889	CW	Q2	2026-06-23 16:54:53.648721+03	2026-06-23 16:55:17.537191+03
f2cff3b8-7e7d-44a0-a81b-44b365c55a15	131b85f5-42bf-4d8f-b39f-3b7883e79810	181E181E1E98E698F8181E0698780618981E98801E	Unknown-4	Unknown-4	112.5	635	CW	Q2	2026-06-23 16:54:52.915886+03	2026-06-23 16:55:17.685174+03
ef858dd9-5085-4fd8-a207-1521eb36f5c5	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	112.5	635	CW	Q2	2026-06-23 16:54:53.118831+03	2026-06-23 16:55:17.685174+03
08243e36-058b-4789-af0e-330c78a3a0c4	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E698F8981E98801E	Unknown-5	Unknown-5	135	762	CW	Q2	2026-06-23 16:54:53.200409+03	2026-06-23 16:55:17.685174+03
6646538f-0065-45c5-8563-3fed1a95fa1f	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	135	762	CW	Q2	2026-06-23 16:54:53.261519+03	2026-06-23 16:55:17.685174+03
942f228a-88b8-4a99-985f-daa1eae712fc	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66181898F8987860981E98801E	Unknown-6	Unknown-6	135	762	CW	Q2	2026-06-23 16:54:53.343252+03	2026-06-23 16:55:17.685174+03
ed37f614-192a-45a8-a912-55c155230359	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E18981E98801E	Unknown-3	Unknown-3	135	762	CW	Q2	2026-06-23 16:54:53.424569+03	2026-06-23 16:55:17.685174+03
f174d526-41d7-453d-9633-7e01f8e6fa1e	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E1E981E98801E	Unknown-3	Unknown-3	157.5	889	CW	Q2	2026-06-23 16:54:53.485592+03	2026-06-23 16:55:17.685174+03
034dcfb6-d537-429e-98da-18f18681a15f	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	157.5	889	CW	Q2	2026-06-23 16:54:53.566942+03	2026-06-23 16:55:17.685174+03
96b82846-5913-4742-9215-a2f25b2ecf7f	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	157.5	889	CW	Q2	2026-06-23 16:54:53.648721+03	2026-06-23 16:55:17.685174+03
dbb17e7c-0b0c-42d1-b58b-749166abc5b3	131b85f5-42bf-4d8f-b39f-3b7883e79810	181E181E1E98E698F8181E0698780618981E98801E	Unknown-4	Unknown-4	112.5	635	CW	Q2	2026-06-23 16:54:52.915886+03	2026-06-23 16:55:17.830073+03
3f7c6835-b69d-4247-9afb-04159e5d29e3	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	112.5	635	CW	Q2	2026-06-23 16:54:53.118831+03	2026-06-23 16:55:17.830073+03
7470200e-f398-4dd7-8f83-a01a32462f3d	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E698F8981E98801E	Unknown-5	Unknown-5	135	762	CW	Q2	2026-06-23 16:54:53.200409+03	2026-06-23 16:55:17.830073+03
47ce7a91-bbba-4930-8473-7c5f6e1e7891	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	135	762	CW	Q2	2026-06-23 16:54:53.261519+03	2026-06-23 16:55:17.830073+03
fee6ca39-4504-4d0c-ab36-2f1ccb3c277c	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66181898F8987860981E98801E	Unknown-6	Unknown-6	135	762	CW	Q2	2026-06-23 16:54:53.343252+03	2026-06-23 16:55:17.830073+03
3eb29b2a-1963-450f-9404-0cb116d2ca56	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E18981E98801E	Unknown-3	Unknown-3	135	762	CW	Q2	2026-06-23 16:54:53.424569+03	2026-06-23 16:55:17.830073+03
a794f412-311a-405e-8471-7ad9916e3ff2	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7E18181E1E981E98801E	Unknown-3	Unknown-3	157.5	889	CW	Q2	2026-06-23 16:54:53.485592+03	2026-06-23 16:55:17.830073+03
426c2455-a4d7-4e62-bb34-e0a74453188a	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E7818987880981E98801E	Unknown-2	Unknown-2	157.5	889	CW	Q2	2026-06-23 16:54:53.566942+03	2026-06-23 16:55:17.830073+03
94d02960-9d28-4f6e-9ff1-d510f67ec8d9	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E661898E098F898E618981E98801E	Unknown-1	Unknown-1	157.5	889	CW	Q2	2026-06-23 16:54:53.648721+03	2026-06-23 16:55:17.830073+03
c9cdf6df-c2fa-4e42-80a2-001f0f7d1047	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	45	254	CW	Q1	2026-06-23 17:04:56.507124+03	2026-06-23 17:05:16.5534+03
083db9af-fa46-4d8a-a3df-6edf50ecadee	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	67.5	381	CW	Q1	2026-06-23 17:04:56.935359+03	2026-06-23 17:05:16.5534+03
40c39db3-3a39-488f-acda-cc1148161914	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	112.5	635	CW	Q2	2026-06-23 17:04:57.362268+03	2026-06-23 17:05:16.5534+03
af64a42e-84e6-4493-8417-6ce4386c2d87	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	135	762	CW	Q2	2026-06-23 17:04:57.769182+03	2026-06-23 17:05:16.5534+03
4d0b4277-3c64-41ff-abf9-89604e29cf7d	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	157.5	889	CW	Q2	2026-06-23 17:04:57.850151+03	2026-06-23 17:05:16.5534+03
582de4cc-64dd-4ea4-aeeb-dc3f97eb868a	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	157.5	889	CW	Q2	2026-06-23 17:04:58.012766+03	2026-06-23 17:05:16.5534+03
35b442db-7d4b-4b50-8d1c-24781e512a4a	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	180	1016	CW	Q3	2026-06-23 17:04:58.154599+03	2026-06-23 17:05:16.5534+03
de7eea9c-24e8-46b7-bc44-a6ba3e273899	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	180	1016	CW	Q3	2026-06-23 17:04:58.236375+03	2026-06-23 17:05:16.5534+03
4f68fee5-b20e-4734-8ab6-ec652b2ad281	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	180	1016	CW	Q3	2026-06-23 17:04:58.297963+03	2026-06-23 17:05:16.5534+03
1038bd55-ae3b-4f13-ab9c-b5031dece059	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	202.5	1143	CW	Q3	2026-06-23 17:04:58.379129+03	2026-06-23 17:05:16.5534+03
191b443c-2aa1-4be2-9b2c-2ccc68ed0bf9	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	202.5	1143	CW	Q3	2026-06-23 17:04:58.460803+03	2026-06-23 17:05:16.5534+03
38e47f97-0c29-4fad-8e03-cd3dffc8778a	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	225	1270	CW	Q3	2026-06-23 17:04:58.602397+03	2026-06-23 17:05:16.5534+03
8a4b323f-e90e-41e2-beb0-37ae92177ba1	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	225	1270	CW	Q3	2026-06-23 17:04:58.745277+03	2026-06-23 17:05:16.5534+03
3bc7b481-7908-4270-b8c2-acb02887abb1	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	360	1905	CW	Q1	2026-06-23 17:04:59.944725+03	2026-06-23 17:05:16.5534+03
dda562f9-3b8e-4711-b69a-e2259d346004	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	45	254	CW	Q1	2026-06-23 17:04:56.507124+03	2026-06-23 17:09:33.309923+03
34d8b8af-ca1e-41a1-a65c-0a6a207dd64b	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	67.5	381	CW	Q1	2026-06-23 17:04:56.935359+03	2026-06-23 17:09:33.309923+03
2cfe7d56-c3ea-4047-89de-4f426d5f68f4	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	112.5	635	CW	Q2	2026-06-23 17:04:57.362268+03	2026-06-23 17:09:33.309923+03
3b8b1bd9-c90a-42a2-8666-f9a5c9d4ca48	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	135	762	CW	Q2	2026-06-23 17:04:57.769182+03	2026-06-23 17:09:33.309923+03
ab8f9517-863d-467b-81dc-827a82b8120c	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	157.5	889	CW	Q2	2026-06-23 17:04:57.850151+03	2026-06-23 17:09:33.309923+03
59a1568a-ace9-4147-97c9-42e4b3155767	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	157.5	889	CW	Q2	2026-06-23 17:04:58.012766+03	2026-06-23 17:09:33.309923+03
8cd8a2e7-e7a1-4206-a3a1-5cbbd6020f19	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	180	1016	CW	Q3	2026-06-23 17:04:58.154599+03	2026-06-23 17:09:33.309923+03
ca60b246-125a-4723-bf5d-aaf0e9c34c06	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	180	1016	CW	Q3	2026-06-23 17:04:58.236375+03	2026-06-23 17:09:33.309923+03
6d154275-ad14-4610-8478-e15884716a56	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	180	1016	CW	Q3	2026-06-23 17:04:58.297963+03	2026-06-23 17:09:33.309923+03
c79a8519-c7a3-4344-aafe-4afac419d163	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	202.5	1143	CW	Q3	2026-06-23 17:04:58.379129+03	2026-06-23 17:09:33.309923+03
13a97daa-4331-45eb-bf04-1fab3dcf2ef3	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	202.5	1143	CW	Q3	2026-06-23 17:04:58.460803+03	2026-06-23 17:09:33.309923+03
745c3f89-f5e1-442a-960a-f0bdb66b1435	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	225	1270	CW	Q3	2026-06-23 17:04:58.602397+03	2026-06-23 17:09:33.309923+03
e37d5a13-90df-4f0e-9b77-c2f7d7f17831	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	225	1270	CW	Q3	2026-06-23 17:04:58.745277+03	2026-06-23 17:09:33.309923+03
db5e580c-674e-4366-82fa-464582b7c651	131b85f5-42bf-4d8f-b39f-3b7883e79810	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	360	1905	CW	Q1	2026-06-23 17:04:59.944725+03	2026-06-23 17:09:33.309923+03
8c7dc98f-c330-498b-a821-1940f08b226e	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	0	0	CW	Q1	2026-06-23 17:31:54.598954+03	2026-06-23 17:32:01.773743+03
fb8583c8-8e0e-4b61-a1ec-bb9da45279cc	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	22.5	127	CW	Q1	2026-06-23 17:31:54.923287+03	2026-06-23 17:32:01.773743+03
8d8a7ad7-6a80-4cd3-bb40-633b49be607a	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	225	1270	CW	Q3	2026-06-23 17:31:57.261936+03	2026-06-23 17:32:01.773743+03
ba7f96ff-498f-4180-b975-d8087ec5e2dd	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	247.5	1397	CW	Q3	2026-06-23 17:31:57.566199+03	2026-06-23 17:32:01.773743+03
911ec2d8-649f-4ce0-be88-12c58452425b	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	270	1524	CW	Q4	2026-06-23 17:31:57.911349+03	2026-06-23 17:32:01.773743+03
991dd820-3c3d-48e6-aa85-b8e432551848	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	292.5	1651	CW	Q4	2026-06-23 17:31:58.074539+03	2026-06-23 17:32:01.773743+03
149ec0e0-3523-4f60-a1de-429f22963e61	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	292.5	1651	CW	Q4	2026-06-23 17:31:58.156037+03	2026-06-23 17:32:01.773743+03
674fd564-bf8f-4196-863f-c5dd9b84e510	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	292.5	1651	CW	Q4	2026-06-23 17:31:58.217331+03	2026-06-23 17:32:01.773743+03
168233a7-21f9-4687-8605-05d421ed1988	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	315	1778	CW	Q4	2026-06-23 17:31:58.379855+03	2026-06-23 17:32:01.773743+03
4ebcd3ff-c0e1-4953-b214-537c9873b9dd	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	360	1905	CW	Q1	2026-06-23 17:31:58.522016+03	2026-06-23 17:32:01.773743+03
3375b343-2dbe-494a-995d-5bfca2a615b8	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	360	1905	CW	Q1	2026-06-23 17:31:58.60335+03	2026-06-23 17:32:01.773743+03
94df794d-77f2-4a0c-8683-4b4f03c9d82f	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	360	1905	CW	Q1	2026-06-23 17:31:58.684211+03	2026-06-23 17:32:01.773743+03
ac3a7370-a379-4fe4-b3b3-ea4b3887e6da	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	360	1905	CW	Q1	2026-06-23 17:31:58.745422+03	2026-06-23 17:32:01.773743+03
58ca67f8-f239-4a9a-bc1e-0a121a62ec00	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	360	1905	CW	Q1	2026-06-23 17:31:58.82735+03	2026-06-23 17:32:01.773743+03
8697a735-2634-4beb-9c0f-355b47cb66a5	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	0	0	CW	Q1	2026-06-23 17:32:08.254348+03	2026-06-23 17:32:18.218572+03
db214b6b-80e9-49db-9170-4e9fb3ef33f9	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	0	0	CW	Q1	2026-06-23 17:32:08.335906+03	2026-06-23 17:32:18.218572+03
f23f7529-a416-43e6-b7ac-210a85df595d	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	0	0	CW	Q1	2026-06-23 17:32:08.417383+03	2026-06-23 17:32:18.218572+03
4988258e-d026-40c5-a167-fece5868009f	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	22.5	127	CW	Q1	2026-06-23 17:32:08.701709+03	2026-06-23 17:32:18.218572+03
55880ad5-f3c6-4732-9a6f-e2fe4f230677	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	45	254	CW	Q1	2026-06-23 17:32:08.783276+03	2026-06-23 17:32:18.218572+03
20512ee4-8158-44e8-8337-e0c9015b64d4	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	67.5	381	CW	Q1	2026-06-23 17:32:09.086826+03	2026-06-23 17:32:18.218572+03
73a55c15-739d-4988-b3fe-5225d95cc8d2	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	67.5	381	CW	Q1	2026-06-23 17:32:09.168142+03	2026-06-23 17:32:18.218572+03
a26ca4cd-2f6f-4da8-9b89-cf746bf805da	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	67.5	381	CW	Q1	2026-06-23 17:32:09.229402+03	2026-06-23 17:32:18.218572+03
87f0b310-8a94-44c4-b08c-fbfa30619854	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	90	508	CW	Q2	2026-06-23 17:32:09.311309+03	2026-06-23 17:32:18.218572+03
99afa207-f6a4-4c1a-b374-3177dc0d2acf	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	90	508	CW	Q2	2026-06-23 17:32:09.534213+03	2026-06-23 17:32:18.218572+03
46c61abe-35cd-4552-944d-13df390a4fde	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	112.5	635	CW	Q2	2026-06-23 17:32:09.615585+03	2026-06-23 17:32:18.218572+03
f1c2535c-f550-4507-8a84-994e91937833	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	112.5	635	CW	Q2	2026-06-23 17:32:09.757571+03	2026-06-23 17:32:18.218572+03
f7f48c5f-1a16-4c25-b8c0-de6372dae5ff	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	135	762	CW	Q2	2026-06-23 17:32:09.839116+03	2026-06-23 17:32:18.218572+03
4c16406a-869c-4a91-b8d1-b74642f455de	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	157.5	889	CW	Q2	2026-06-23 17:32:10.143852+03	2026-06-23 17:32:18.218572+03
7a2d9542-61b5-4e61-bebf-013d728fe51b	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66381E60981E8618981E98801E	Tag-20	Tag-20	157.5	889	CW	Q2	2026-06-23 17:32:10.287591+03	2026-06-23 17:32:18.218572+03
40edc148-862f-4785-8c0f-fd0bcd373c5a	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	247.5	1397	CW	Q3	2026-06-23 17:32:11.343539+03	2026-06-23 17:32:18.218572+03
344a9c01-3959-4b6b-9cb9-cef75a426fa5	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	270	1524	CW	Q4	2026-06-23 17:32:11.647975+03	2026-06-23 17:32:18.218572+03
fa33ab96-3ab8-49b7-8888-ad391589eecf	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	315	1778	CW	Q4	2026-06-23 17:32:12.018331+03	2026-06-23 17:32:18.218572+03
e616ab2d-1f4a-4ee9-9500-7ab025475fe0	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	315	1778	CW	Q4	2026-06-23 17:32:12.099243+03	2026-06-23 17:32:18.218572+03
db0b0bd4-d3d0-421d-a00f-f1828f0aad6e	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	315	1778	CW	Q4	2026-06-23 17:32:12.160191+03	2026-06-23 17:32:18.218572+03
c16087da-eca9-4f47-863f-efe1d73be53d	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	360	1905	CW	Q1	2026-06-23 17:32:12.323068+03	2026-06-23 17:32:18.218572+03
46ed59de-6dfa-433f-8fce-babfe0d843d4	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	360	1905	CW	Q1	2026-06-23 17:32:12.465938+03	2026-06-23 17:32:18.218572+03
00bdc34e-07fe-4a73-a1ec-e2b6ea75d2c0	f14bdc3f-9822-43ab-9ef1-820f8f688526	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	360	1905	CW	Q1	2026-06-23 17:32:12.62844+03	2026-06-23 17:32:18.218572+03
de947239-2620-4590-8ad8-e31a571f12e8	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	0	0	CW	Q1	2026-06-23 18:34:18.423874+03	2026-06-23 18:35:40.222098+03
90811e92-fb81-4732-a9a6-57d379f37029	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	0	0	CW	Q1	2026-06-23 18:34:18.505168+03	2026-06-23 18:35:40.222098+03
f8d5779f-ef4f-4b70-9780-13190dc8bd1c	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	0	0	CW	Q1	2026-06-23 18:34:18.647203+03	2026-06-23 18:35:40.222098+03
4efd81c0-005d-46ab-be79-0469373e8e4e	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618F8E68098801E	Tag-2	Tag-2	22.5	127	CW	Q1	2026-06-23 18:34:18.728174+03	2026-06-23 18:35:40.222098+03
31bd08f4-e9fe-41d3-9135-6b6ee6084fbc	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	22.5	127	CW	Q1	2026-06-23 18:34:18.809473+03	2026-06-23 18:35:40.222098+03
adfcbaf3-759c-4888-962b-059f7937bdbf	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	45	254	CW	Q1	2026-06-23 18:34:18.95201+03	2026-06-23 18:35:40.222098+03
e9a394f8-7a13-4fdc-9dc9-8b466644b02a	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	45	254	CW	Q1	2026-06-23 18:34:19.033477+03	2026-06-23 18:35:40.222098+03
b3e2bd34-fd5d-4401-b06a-2519e9a89376	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	45	254	CW	Q1	2026-06-23 18:34:19.094507+03	2026-06-23 18:35:40.222098+03
f3042018-7fc7-4a0d-bf65-bab8eade7937	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	67.5	381	CW	Q1	2026-06-23 18:34:19.257183+03	2026-06-23 18:35:40.222098+03
6ad4bd9a-a293-4845-95f4-aa04d24ff63b	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	67.5	381	CW	Q1	2026-06-23 18:34:19.318477+03	2026-06-23 18:35:40.222098+03
06913e5d-47fa-421c-8bf5-53a2daf6b47f	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	67.5	381	CW	Q1	2026-06-23 18:34:19.400197+03	2026-06-23 18:35:40.222098+03
351065f0-6941-43fd-bcf1-d0093b4f7944	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	90	508	CW	Q2	2026-06-23 18:34:19.543169+03	2026-06-23 18:35:40.222098+03
d69dd432-7e08-46c8-913c-3c8426666dca	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	90	508	CW	Q2	2026-06-23 18:34:19.706537+03	2026-06-23 18:35:40.222098+03
56df58d5-3bf0-49ab-af44-ac6eda2abd9f	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	112.5	635	CW	Q2	2026-06-23 18:34:19.768275+03	2026-06-23 18:35:40.222098+03
2a0f4fe4-8d40-4bef-bb91-e4bb7ce128e2	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	112.5	635	CW	Q2	2026-06-23 18:34:19.849596+03	2026-06-23 18:35:40.222098+03
4730f4f8-b64a-4fa7-ab74-0be3ca3210ec	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	135	762	CW	Q2	2026-06-23 18:34:20.011471+03	2026-06-23 18:35:40.222098+03
e433fcaf-8b33-4e44-881e-ae9f3f2c7bc3	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	135	762	CW	Q2	2026-06-23 18:34:20.152848+03	2026-06-23 18:35:40.222098+03
fc76dd55-470d-499e-92d1-980044f7a849	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	157.5	889	CW	Q2	2026-06-23 18:34:20.295593+03	2026-06-23 18:35:40.222098+03
cec6210a-df5d-48a4-9aca-73f19eba37f3	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	157.5	889	CW	Q2	2026-06-23 18:34:20.458943+03	2026-06-23 18:35:40.222098+03
40072cd9-cf83-4b9b-9172-cbaa0ef0804e	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	180	1016	CW	Q3	2026-06-23 18:34:20.601259+03	2026-06-23 18:35:40.222098+03
fe118748-d684-4559-828e-95b54b0d9281	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	180	1016	CW	Q3	2026-06-23 18:34:20.683039+03	2026-06-23 18:35:40.222098+03
818b830a-f1cd-47be-9491-9e074ada3c70	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	180	1016	CW	Q3	2026-06-23 18:34:20.744257+03	2026-06-23 18:35:40.222098+03
c16301b3-d9e3-442d-9de2-33dc08093c8e	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E66F88098E0181EE68098801E	Tag-10	Tag-10	202.5	1143	CW	Q3	2026-06-23 18:34:20.825477+03	2026-06-23 18:35:40.222098+03
f9a72c20-21ea-4d3b-b2d2-8880f5af0b60	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	202.5	1143	CW	Q3	2026-06-23 18:34:20.906587+03	2026-06-23 18:35:40.222098+03
9737936e-f26c-49be-8cb1-1653a1f5b36d	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	202.5	1143	CW	Q3	2026-06-23 18:34:21.049919+03	2026-06-23 18:35:40.222098+03
849b7db1-5464-4430-a04a-686b89eac917	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	225	1270	CW	Q3	2026-06-23 18:34:21.131452+03	2026-06-23 18:35:40.222098+03
f58d21d8-df47-4eee-a1e2-eebccdb6b7d7	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	225	1270	CW	Q3	2026-06-23 18:34:21.192879+03	2026-06-23 18:35:40.222098+03
60729de3-0be1-40f9-b93c-dcaaca20e79b	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E607E98F818981E98801E	Tag-20	Tag-20	247.5	1397	CW	Q3	2026-06-23 18:34:21.355494+03	2026-06-23 18:35:40.222098+03
14e2ccd8-99ab-4796-81d0-00f8cc04cf31	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	247.5	1397	CW	Q3	2026-06-23 18:34:21.416873+03	2026-06-23 18:35:40.222098+03
02622314-a0e7-40db-b6fc-3139035e87b7	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	247.5	1397	CW	Q3	2026-06-23 18:34:21.497974+03	2026-06-23 18:35:40.222098+03
e1351534-7b08-4b47-936f-13f1405f895b	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	270	1524	CW	Q4	2026-06-23 18:34:21.639982+03	2026-06-23 18:35:40.222098+03
07a5be6c-924d-4e37-9c96-2ca19f36b284	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	270	1524	CW	Q4	2026-06-23 18:34:21.721101+03	2026-06-23 18:35:40.222098+03
3e539069-e5c1-46bc-b161-db7ddb38a586	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	270	1524	CW	Q4	2026-06-23 18:34:21.802329+03	2026-06-23 18:35:40.222098+03
835534b7-00c6-44df-a16f-b6c79629fbe0	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E668098E0181EE68098801E	Tag-19	Tag-19	292.5	1651	CW	Q4	2026-06-23 18:34:21.863094+03	2026-06-23 18:35:40.222098+03
2e9601ea-375e-4662-80eb-771571bd1d04	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	292.5	1651	CW	Q4	2026-06-23 18:34:21.94375+03	2026-06-23 18:35:40.222098+03
1d590b2b-6b83-4548-939f-42e2ccb58570	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	292.5	1651	CW	Q4	2026-06-23 18:34:22.024587+03	2026-06-23 18:35:40.222098+03
8f58ed1d-bffa-4e16-ab08-0fa03d2d2213	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018F87E98E6981E60981E8618981E98801E	Unknown-6	Unknown-6	292.5	1651	CW	Q4	2026-06-23 18:34:22.106475+03	2026-06-23 18:35:40.222098+03
b3920c50-491e-4972-905b-aaad6b441c56	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	315	1778	CW	Q4	2026-06-23 18:34:22.167418+03	2026-06-23 18:35:40.222098+03
42e46bb0-56e3-488c-a7b3-bd6c6e7382f2	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	315	1778	CW	Q4	2026-06-23 18:34:22.249161+03	2026-06-23 18:35:40.222098+03
dc6f81f1-f702-4436-a430-03d69f83c889	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	315	1778	CW	Q4	2026-06-23 18:34:22.330216+03	2026-06-23 18:35:40.222098+03
c921336b-4ddf-4702-89dc-77f60c1a86fd	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E668098E0181EE68098801E	Tag-19	Tag-19	360	1905	CW	Q1	2026-06-23 18:34:22.39147+03	2026-06-23 18:35:40.222098+03
a4d42d39-cb3e-405c-b12c-ae6389ceb398	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	360	1905	CW	Q1	2026-06-23 18:34:22.472564+03	2026-06-23 18:35:40.222098+03
9959b3c2-a856-4f92-8700-efa75a6847de	e2dc5bf0-db01-4ce2-969f-144ab1a5a45a	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	360	1905	CW	Q1	2026-06-23 18:34:22.778449+03	2026-06-23 18:35:40.222098+03
f51815d7-8e18-4f1b-81d0-3603b84d8152	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	22.5	127	CW	Q1	2026-06-24 17:37:49.490445+03	2026-06-24 17:37:58.34947+03
e3ea2d6f-6b6b-4196-ac19-99b8a8030373	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	67.5	381	CW	Q1	2026-06-24 17:37:49.835713+03	2026-06-24 17:37:58.34947+03
71ab79d1-44a9-4f49-b97a-845e1225bfbd	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	90	508	CW	Q2	2026-06-24 17:37:50.262079+03	2026-06-24 17:37:58.34947+03
4941d11b-f61c-482d-965d-8ade15fe0b90	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	157.5	889	CW	Q2	2026-06-24 17:37:50.973719+03	2026-06-24 17:37:58.34947+03
88235bda-574f-47a0-970d-5d4570bb5a94	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	157.5	889	CW	Q2	2026-06-24 17:37:51.035084+03	2026-06-24 17:37:58.34947+03
b190229f-2c7b-4fdf-833d-ac9a5f00d343	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	180	1016	CW	Q3	2026-06-24 17:37:51.197974+03	2026-06-24 17:37:58.34947+03
74046bdc-b58b-45a5-a37a-1e0e16761992	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	180	1016	CW	Q3	2026-06-24 17:37:51.258953+03	2026-06-24 17:37:58.34947+03
d1896df8-0d94-4b1d-89cd-94a9e5547890	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E60981E8618981E98801E	Tag-20	Tag-20	180	1016	CW	Q3	2026-06-24 17:37:51.340291+03	2026-06-24 17:37:58.34947+03
adb684fa-3e85-4784-a25d-93cb6937c14d	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	180	1016	CW	Q3	2026-06-24 17:37:51.421788+03	2026-06-24 17:37:58.34947+03
0fbcaf78-ef7c-4871-8ba8-bb5bdbaa5782	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	225	1270	CW	Q3	2026-06-24 17:37:51.808123+03	2026-06-24 17:37:58.34947+03
3423c0bb-797f-4770-b699-76fadce45dee	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	247.5	1397	CW	Q3	2026-06-24 17:37:52.114055+03	2026-06-24 17:37:58.34947+03
2e44b336-f4e8-48a6-8ff3-d0b379d26bbc	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	270	1524	CW	Q4	2026-06-24 17:37:52.439639+03	2026-06-24 17:37:58.34947+03
b168e4b6-8ca1-4cb4-9884-a53177d92730	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	315	1778	CW	Q4	2026-06-24 17:37:52.764556+03	2026-06-24 17:37:58.34947+03
ec5551d5-e16c-442f-8427-89a59da23f1b	371585a8-73c5-4a79-883f-94f891ad2316	186098E018981E66981E661898E0181EE68098801E	Tag-19	Tag-19	360	1905	CW	Q1	2026-06-24 17:37:53.111422+03	2026-06-24 17:37:58.34947+03
75dc426a-f72b-4fd0-8dc1-e1c322ff14f7	2511620d-16e1-4b06-acf3-664b7ebbce4c	4187575814	Unknown-1	Unknown-1	0	0	CW	Q1	2026-06-24 20:39:38.747077+03	2026-06-24 20:39:57.660151+03
0b5a1bcc-c14d-4cba-83c6-4ff0c082fea9	2511620d-16e1-4b06-acf3-664b7ebbce4c	4187575814	Unknown-1	Unknown-1	22.5	127	CW	Q1	2026-06-24 20:39:39.073409+03	2026-06-24 20:39:57.660151+03
e159d2e5-a60b-4cf6-95b8-3d183c7387a4	2511620d-16e1-4b06-acf3-664b7ebbce4c	4187575814	Unknown-1	Unknown-1	45	254	CW	Q1	2026-06-24 20:39:39.397415+03	2026-06-24 20:39:57.660151+03
d28b418c-5d60-4a32-8c39-987ff810db96	2511620d-16e1-4b06-acf3-664b7ebbce4c	4187575814	Unknown-1	Unknown-1	360	1905	CW	Q1	2026-06-24 20:39:42.867249+03	2026-06-24 20:39:57.660151+03
ddb901b5-4dfd-424e-8d93-1d7ada6e119c	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187574790	Unknown-1	Unknown-1	0	0	CW	Q1	2026-06-24 21:32:13.230919+03	2026-06-24 21:32:23.006754+03
6e1bc62a-46b3-4f73-82dd-69cfeea61c3f	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187575814	Unknown-2	Unknown-2	67.5	381	CW	Q1	2026-06-24 21:32:14.044285+03	2026-06-24 21:32:23.006754+03
1ded2be7-f7ef-455d-9559-f8a043246035	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187575814	Unknown-2	Unknown-2	90	508	CW	Q2	2026-06-24 21:32:14.369368+03	2026-06-24 21:32:23.006754+03
5b4a0d4e-07e4-46a5-b190-8a9d293e6910	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187575814	Unknown-2	Unknown-2	112.5	635	CW	Q2	2026-06-24 21:32:14.694144+03	2026-06-24 21:32:23.006754+03
8e3b15f7-78d7-4f37-ac71-ee3c4cf31069	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187574790	Unknown-1	Unknown-1	292.5	1651	CW	Q4	2026-06-24 21:32:16.806202+03	2026-06-24 21:32:23.006754+03
7a69139d-733e-457c-91d9-ccdfde7eb2b4	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187574790	Unknown-1	Unknown-1	360	1905	CW	Q1	2026-06-24 21:32:17.150091+03	2026-06-24 21:32:23.006754+03
78edbfb0-7428-4859-b94b-3458bb3ca643	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187574790	Unknown-1	Unknown-1	360	1905	CW	Q1	2026-06-24 21:32:17.475653+03	2026-06-24 21:32:23.006754+03
b799d040-873c-4d7b-86cb-0f479f92e2a9	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187574790	Unknown-1	Unknown-1	0	0	CW	Q1	2026-06-24 21:33:41.803962+03	2026-06-24 21:35:00.683354+03
0617f7a6-5d03-45a3-992c-4304d15f73d1	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187574790	Unknown-1	Unknown-1	22.5	127	CW	Q1	2026-06-24 21:33:42.230924+03	2026-06-24 21:35:00.683354+03
7979667e-a03a-4dc2-b33f-1db2e1257a49	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187575814	Unknown-2	Unknown-2	90	508	CW	Q2	2026-06-24 21:33:42.921968+03	2026-06-24 21:35:00.683354+03
2ff5c93b-668b-4cf0-b07b-466104cfd2aa	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187575814	Unknown-2	Unknown-2	112.5	635	CW	Q2	2026-06-24 21:33:43.246751+03	2026-06-24 21:35:00.683354+03
bbb63e6e-d79f-4d21-83ca-b40933b73bc5	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187575814	Unknown-2	Unknown-2	135	762	CW	Q2	2026-06-24 21:33:43.572905+03	2026-06-24 21:35:00.683354+03
d3b5942f-690f-4608-8401-e97b346aa57e	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187574790	Unknown-1	Unknown-1	315	1778	CW	Q4	2026-06-24 21:33:45.689808+03	2026-06-24 21:35:00.683354+03
3b53970e-ae6d-4907-8527-821595f5d77b	9417ec99-b463-4cd1-b726-e7b31f2e0407	4187574790	Unknown-1	Unknown-1	360	1905	CW	Q1	2026-06-24 21:33:46.035185+03	2026-06-24 21:35:00.683354+03
93ac752a-21df-4e49-a8a7-cb815477e01f	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	180	1016	CW	Q3	2026-06-24 21:53:29.899389+03	2026-06-24 21:53:40.481186+03
c2e40925-bd27-436a-ba48-6079c8490e13	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	202.5	1143	CW	Q3	2026-06-24 21:53:30.204345+03	2026-06-24 21:53:40.481186+03
fff70b65-9429-4b96-bbb6-2b4eb6fb773c	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	225	1270	CW	Q3	2026-06-24 21:53:30.529062+03	2026-06-24 21:53:40.481186+03
341be93a-2a36-4ffd-9391-2acc3187078a	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	180	1016	CW	Q3	2026-06-24 21:53:29.899389+03	2026-06-24 21:53:47.089927+03
946aad44-de8c-4d3f-8b3a-6edffe9a553d	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	202.5	1143	CW	Q3	2026-06-24 21:53:30.204345+03	2026-06-24 21:53:47.089927+03
fca6e438-bc28-42dd-a2c9-c56752265d43	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	225	1270	CW	Q3	2026-06-24 21:53:30.529062+03	2026-06-24 21:53:47.089927+03
0fd2b353-9350-4287-849c-2a5bd828ea67	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	180	1016	CW	Q3	2026-06-24 21:53:29.899389+03	2026-06-24 21:53:47.684124+03
6cd117ee-d81a-42cd-8a2d-3289e961f2ab	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	202.5	1143	CW	Q3	2026-06-24 21:53:30.204345+03	2026-06-24 21:53:47.684124+03
97383ec0-1545-43fe-93c5-6f9fe9b62339	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	225	1270	CW	Q3	2026-06-24 21:53:30.529062+03	2026-06-24 21:53:47.684124+03
e69a1334-81e5-48bd-b56b-6e356e64cd2e	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	180	1016	CW	Q3	2026-06-24 21:53:29.899389+03	2026-06-24 21:53:48.009862+03
3da93e22-172a-4d2e-8ad9-14e08c26bacc	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	202.5	1143	CW	Q3	2026-06-24 21:53:30.204345+03	2026-06-24 21:53:48.009862+03
77fba63a-13e2-41dd-a767-e5304850432b	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	225	1270	CW	Q3	2026-06-24 21:53:30.529062+03	2026-06-24 21:53:48.009862+03
dbca43bf-e482-4e02-9954-2401dd20eef1	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	180	1016	CW	Q3	2026-06-24 21:53:29.899389+03	2026-06-24 21:53:48.338403+03
9fee6bc4-0a3f-44e6-b259-343ada3f6e80	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	202.5	1143	CW	Q3	2026-06-24 21:53:30.204345+03	2026-06-24 21:53:48.338403+03
37227edd-606d-42ae-8728-6ea0729c5218	01cf57e1-f1ae-45bd-b406-0679391273f1	4187575814	Unknown-1	Unknown-1	225	1270	CW	Q3	2026-06-24 21:53:30.529062+03	2026-06-24 21:53:48.338403+03
ea86713b-4a65-4e5b-9f12-a0ef80ffa241	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187574790	Unknown-1	Unknown-1	157.5	889	CW	Q2	2026-06-24 22:04:24.363247+03	2026-06-24 22:04:33.015429+03
38c3cd48-57c6-4776-ab1c-57518a657dbb	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187574790	Unknown-1	Unknown-1	180	1016	CW	Q3	2026-06-24 22:04:24.66806+03	2026-06-24 22:04:33.015429+03
c0d1a2df-eb10-4feb-9599-ad750e3bd6e3	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187574790	Unknown-1	Unknown-1	225	1270	CW	Q3	2026-06-24 22:04:25.013243+03	2026-06-24 22:04:33.015429+03
0315028f-2cff-4d91-a0e6-3df4c4c1d60e	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187575814	Unknown-2	Unknown-2	247.5	1397	CW	Q3	2026-06-24 22:04:25.299329+03	2026-06-24 22:04:33.015429+03
20d4178e-f5f5-475a-9853-96e25f0b8294	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187575814	Unknown-2	Unknown-2	270	1524	CW	Q4	2026-06-24 22:04:25.603976+03	2026-06-24 22:04:33.015429+03
17774199-716e-4124-bcf2-9281c3430107	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187575814	Unknown-2	Unknown-2	292.5	1651	CW	Q4	2026-06-24 22:04:25.929804+03	2026-06-24 22:04:33.015429+03
620d0d2b-ed3a-4abc-aed5-c98e495cefdb	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187575814	Unknown-1	Unknown-1	0	0	CW	Q1	2026-06-24 22:05:40.333465+03	2026-06-24 22:06:10.030818+03
63a1b9d1-6349-440d-a690-7316f7d017ff	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187574790	Unknown-2	Unknown-2	180	1016	CW	Q3	2026-06-24 22:05:42.672223+03	2026-06-24 22:06:10.030818+03
f3938786-9409-4ed6-812c-08968b797f95	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187574790	Unknown-2	Unknown-2	225	1270	CW	Q3	2026-06-24 22:05:43.118567+03	2026-06-24 22:06:10.030818+03
e328fefd-5746-4e8d-bb84-3d84cd5dbd37	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187574790	Unknown-2	Unknown-2	247.5	1397	CW	Q3	2026-06-24 22:05:43.443319+03	2026-06-24 22:06:10.030818+03
ebdc9d73-d194-48b3-96c9-77287f14ee34	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187575814	Unknown-1	Unknown-1	292.5	1651	CW	Q4	2026-06-24 22:05:43.828728+03	2026-06-24 22:06:10.030818+03
ab6278a8-1336-43f7-9604-2b8e25a06fd3	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187575814	Unknown-1	Unknown-1	315	1778	CW	Q4	2026-06-24 22:05:44.17401+03	2026-06-24 22:06:10.030818+03
d9a8110d-da2c-4ce5-a620-51ce08ec3be1	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187575814	Unknown-1	Unknown-1	360	1905	CW	Q1	2026-06-24 22:05:44.499433+03	2026-06-24 22:06:10.030818+03
e40605b5-5251-4b45-9311-9cb2f406447c	bdc7f8a0-c9fe-4d1f-9cfd-a0bf45817a9e	4187574790	Tag-20	Tag-20	270	1524	CW	Q4	2026-06-24 22:40:46.882087+03	2026-06-24 22:40:53.812301+03
9dfecb47-bb74-40a4-9322-af9133e86afb	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	0	0	CW	Q1	2026-06-24 23:31:23.813788+03	2026-06-24 23:31:33.738685+03
f98e8c90-d44e-43f0-aa08-12867ce3da50	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	22.5	127	CW	Q1	2026-06-24 23:31:24.139588+03	2026-06-24 23:31:33.738685+03
37b55027-7efa-4605-9c84-09cff85bd140	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	360	1905	CW	Q1	2026-06-24 23:31:27.872894+03	2026-06-24 23:31:33.738685+03
102253ff-d972-40a0-b9ad-d1ab792c152e	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	360	1905	CW	Q1	2026-06-24 23:31:28.198317+03	2026-06-24 23:31:33.738685+03
8a47bec8-ff9a-4ead-af95-96b2aba03666	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	45	254	CW	Q1	2026-06-24 23:55:02.079255+03	2026-06-24 23:56:12.659486+03
72513722-52df-444e-8d7d-1002de198add	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	135	762	CW	Q2	2026-06-24 23:55:03.094006+03	2026-06-24 23:56:12.659486+03
67dd6e8a-4368-476f-b464-8b712f47375a	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	157.5	889	CW	Q2	2026-06-24 23:55:03.398481+03	2026-06-24 23:56:12.659486+03
1dac35e2-d47e-42d8-9610-3ae5b4778ec4	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187576838	Tag-18	Tag-18	157.5	889	CW	Q2	2026-06-24 23:55:03.480362+03	2026-06-24 23:56:12.659486+03
bf0dad53-8e4b-4f42-8c4c-237f73a65035	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	157.5	889	CW	Q2	2026-06-24 23:55:03.561581+03	2026-06-24 23:56:12.659486+03
63dd5ac7-2452-494e-a495-707342baacdc	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187575814	Tag-19	Tag-19	180	1016	CW	Q3	2026-06-24 23:55:03.622186+03	2026-06-24 23:56:12.659486+03
7d576932-7700-442f-842d-66a66c39f7a6	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187577862	Tag-17	Tag-17	180	1016	CW	Q3	2026-06-24 23:55:03.703308+03	2026-06-24 23:56:12.659486+03
1a4344ee-f7b9-4f16-9846-77de78ed6983	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187576838	Tag-18	Tag-18	180	1016	CW	Q3	2026-06-24 23:55:03.784726+03	2026-06-24 23:56:12.659486+03
6311320c-dd45-425e-b27f-f031bee8a3a5	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187577862	Tag-17	Tag-17	202.5	1143	CW	Q3	2026-06-24 23:55:03.865836+03	2026-06-24 23:56:12.659486+03
594d486b-5b74-41ff-a3c9-8a40f66570b1	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	202.5	1143	CW	Q3	2026-06-24 23:55:03.946795+03	2026-06-24 23:56:12.659486+03
ef2a0332-e2f5-4311-9ce3-f1bbad941457	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187575814	Tag-19	Tag-19	202.5	1143	CW	Q3	2026-06-24 23:55:04.02802+03	2026-06-24 23:56:12.659486+03
51407f5e-504f-4e5d-b0c7-d03279320d76	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187576838	Tag-18	Tag-18	202.5	1143	CW	Q3	2026-06-24 23:55:04.108824+03	2026-06-24 23:56:12.659486+03
ec18527f-0c47-4a0a-8df1-931b60f0ae19	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187577862	Tag-17	Tag-17	225	1270	CW	Q3	2026-06-24 23:55:04.169754+03	2026-06-24 23:56:12.659486+03
fadb2ceb-8626-432d-ac6a-0873c938e586	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187578887	Tag-9	Tag-9	225	1270	CW	Q3	2026-06-24 23:55:04.250458+03	2026-06-24 23:56:12.659486+03
96f01b52-b721-46e1-b4f5-7ca614dede6c	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187580935	Tag-11	Tag-11	225	1270	CW	Q3	2026-06-24 23:55:04.331752+03	2026-06-24 23:56:12.659486+03
41322492-20e5-430f-9be3-aa150913b12a	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187581959	Tag-12	Tag-12	247.5	1397	CW	Q3	2026-06-24 23:55:04.413163+03	2026-06-24 23:56:12.659486+03
cdd0ee48-0762-42c7-873b-681021323f7f	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187578886	Tag-16	Tag-16	247.5	1397	CW	Q3	2026-06-24 23:55:04.494972+03	2026-06-24 23:56:12.659486+03
93648128-3a95-4a41-8ce9-776f932f16ee	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	247.5	1397	CW	Q3	2026-06-24 23:55:04.576514+03	2026-06-24 23:56:12.659486+03
b3921ecd-cc00-432f-a4ab-2fadc7fa94d4	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187581958	Tag-13	Tag-13	270	1524	CW	Q4	2026-06-24 23:55:04.658086+03	2026-06-24 23:56:12.659486+03
b48c3301-07a3-4aed-9f94-065a8f390beb	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187578886	Tag-16	Tag-16	270	1524	CW	Q4	2026-06-24 23:55:04.719403+03	2026-06-24 23:56:12.659486+03
46948f48-e0f0-42e1-bfa0-1dc92e386982	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187575814	Tag-19	Tag-19	270	1524	CW	Q4	2026-06-24 23:55:04.800867+03	2026-06-24 23:56:12.659486+03
4c756816-be05-4f7d-91d1-39cb9cfe141d	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187580935	Tag-11	Tag-11	270	1524	CW	Q4	2026-06-24 23:55:04.882642+03	2026-06-24 23:56:12.659486+03
98d72fd1-8a50-40d6-83fa-d7c1426bf4e1	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	292.5	1651	CW	Q4	2026-06-24 23:55:04.963898+03	2026-06-24 23:56:12.659486+03
1a7406ea-6175-451f-804d-89f7d3a37076	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187576838	Tag-18	Tag-18	292.5	1651	CW	Q4	2026-06-24 23:55:05.045046+03	2026-06-24 23:56:12.659486+03
89b0e79c-934b-457d-8629-2b90a17aeec7	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187579911	Tag-10	Tag-10	292.5	1651	CW	Q4	2026-06-24 23:55:05.126929+03	2026-06-24 23:56:12.659486+03
98bd3a62-0c2d-460f-87ec-87362b2650a7	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187570695	Tag-3	Tag-3	315	1778	CW	Q4	2026-06-24 23:55:05.18826+03	2026-06-24 23:56:12.659486+03
bff5735d-ee20-497a-befb-cc1fb23051fe	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	315	1778	CW	Q4	2026-06-24 23:55:05.26952+03	2026-06-24 23:56:12.659486+03
f782b7ed-4401-44b2-98c8-df9af39202d7	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187581958	Tag-13	Tag-13	315	1778	CW	Q4	2026-06-24 23:55:05.350445+03	2026-06-24 23:56:12.659486+03
e4747229-f186-4abf-b4dc-a4abb667637b	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187577862	Tag-17	Tag-17	315	1778	CW	Q4	2026-06-24 23:55:05.431909+03	2026-06-24 23:56:12.659486+03
63b77137-5550-48ea-9613-c2aa6e4b8074	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187578886	Tag-16	Tag-16	360	1905	CW	Q1	2026-06-24 23:55:05.513462+03	2026-06-24 23:56:12.659486+03
847a7b26-d0cb-448d-97d7-e688859120fa	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187576838	Tag-18	Tag-18	360	1905	CW	Q1	2026-06-24 23:55:05.594895+03	2026-06-24 23:56:12.659486+03
67117b4c-7ac7-4b39-ab9a-4bba55646f68	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187580935	Tag-11	Tag-11	360	1905	CW	Q1	2026-06-24 23:55:05.676483+03	2026-06-24 23:56:12.659486+03
73a9d0b8-ed7d-43e6-ba8c-02cbe814a617	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187581959	Tag-12	Tag-12	360	1905	CW	Q1	2026-06-24 23:55:05.737688+03	2026-06-24 23:56:12.659486+03
53badb71-e351-44e0-a6dd-2c1d4ad67118	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	360	1905	CW	Q1	2026-06-24 23:55:05.818825+03	2026-06-24 23:56:12.659486+03
05062c3d-8360-4716-9891-97ec13b7f8b8	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187577862	Tag-17	Tag-17	360	1905	CW	Q1	2026-06-24 23:55:05.900292+03	2026-06-24 23:56:12.659486+03
68fcd52b-c7b9-4c93-9f98-fdac57b5ebb4	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187570695	Tag-3	Tag-3	202.5	1143	CW	Q3	2026-06-24 23:56:49.948381+03	2026-06-24 23:57:48.764563+03
f9bf42b4-0abe-48e3-84d7-3f745d4a8b8e	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187570695	Tag-3	Tag-3	202.5	1143	CW	Q3	2026-06-24 23:56:49.948381+03	2026-06-24 23:57:53.535239+03
f3be6574-81f0-4cef-9a63-7f3853667063	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187570695	Tag-3	Tag-3	202.5	1143	CW	Q3	2026-06-24 23:56:49.948381+03	2026-06-24 23:57:53.92567+03
0cbb193a-7d45-4051-baa3-ba91e5b29f03	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187570695	Tag-3	Tag-3	202.5	1143	CW	Q3	2026-06-24 23:56:49.948381+03	2026-06-24 23:57:54.108101+03
ab7b5b61-494d-406b-b7b5-32169901cd68	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187570695	Tag-3	Tag-3	202.5	1143	CW	Q3	2026-06-24 23:56:49.948381+03	2026-06-24 23:57:54.254631+03
76ea6035-d5b1-4201-bd69-5ce285e72518	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187570695	Tag-3	Tag-3	202.5	1143	CW	Q3	2026-06-24 23:56:49.948381+03	2026-06-24 23:57:54.402695+03
9ec80bf5-c5f1-4f65-b46f-951839a757d8	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187570695	Tag-3	Tag-3	202.5	1143	CW	Q3	2026-06-24 23:56:49.948381+03	2026-06-24 23:57:54.754269+03
3ff7c129-1830-4b45-99b2-69cee2705149	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187577863	Tag-8	Tag-8	225	1270	CW	Q3	2026-06-25 00:12:57.400908+03	2026-06-25 00:13:41.651204+03
85ab5da8-e575-46b9-86fc-43fb36b172ef	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187578887	Tag-9	Tag-9	225	1270	CW	Q3	2026-06-25 00:12:57.482812+03	2026-06-25 00:13:41.651204+03
a8f1ba42-d5ba-4d33-9497-042ff4778b9b	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	247.5	1397	CW	Q3	2026-06-25 00:12:57.564418+03	2026-06-25 00:13:41.651204+03
1f966b2a-2299-4284-8266-71cb84f4f839	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187576839	Tag-7	Tag-7	247.5	1397	CW	Q3	2026-06-25 00:12:57.625895+03	2026-06-25 00:13:41.651204+03
00babc18-fca7-4a3e-b04e-7f45af5ededf	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574791	Tag-5	Tag-5	247.5	1397	CW	Q3	2026-06-25 00:12:57.707694+03	2026-06-25 00:13:41.651204+03
0e2bb4e8-d07e-4705-bc22-f37715ec7d78	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187577863	Tag-8	Tag-8	247.5	1397	CW	Q3	2026-06-25 00:12:57.788665+03	2026-06-25 00:13:41.651204+03
3b9dfebd-cc58-483f-8b80-88bfb0be1232	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	270	1524	CW	Q4	2026-06-25 00:12:57.869807+03	2026-06-25 00:13:41.651204+03
a6b62ef2-8130-47c4-a80e-2bbfc955f721	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187578887	Tag-9	Tag-9	270	1524	CW	Q4	2026-06-25 00:12:57.95172+03	2026-06-25 00:13:41.651204+03
d0176d55-c687-4a6b-8fc3-2f2c86e55cac	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187576838	Tag-18	Tag-18	270	1524	CW	Q4	2026-06-25 00:12:58.033077+03	2026-06-25 00:13:41.651204+03
60e3fed6-b1b4-45fc-93b1-f87f46dd57e0	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187577862	Tag-17	Tag-17	292.5	1651	CW	Q4	2026-06-25 00:12:58.094249+03	2026-06-25 00:13:41.651204+03
25d51d0c-88bf-4f44-b44d-fa2781b1b611	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574790	Tag-20	Tag-20	292.5	1651	CW	Q4	2026-06-25 00:12:58.175852+03	2026-06-25 00:13:41.651204+03
2b500959-a995-4caf-ba96-d10794699002	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187576839	Tag-7	Tag-7	292.5	1651	CW	Q4	2026-06-25 00:12:58.25729+03	2026-06-25 00:13:41.651204+03
8e03ceeb-1926-45b4-b751-bc089089f9c2	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187571719	Tag-2	Tag-2	315	1778	CW	Q4	2026-06-25 00:12:58.338574+03	2026-06-25 00:13:41.651204+03
c50cec62-f32f-485a-b46f-a6c1b191f588	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187578887	Tag-9	Tag-9	315	1778	CW	Q4	2026-06-25 00:12:58.419436+03	2026-06-25 00:13:41.651204+03
0601bf8e-87dd-4d14-ba02-a31cdabf3fee	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187577863	Tag-8	Tag-8	315	1778	CW	Q4	2026-06-25 00:12:58.500551+03	2026-06-25 00:13:41.651204+03
1532f6a7-79f2-4f4d-a7d3-4cceb0fe2055	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574791	Tag-5	Tag-5	315	1778	CW	Q4	2026-06-25 00:12:58.581801+03	2026-06-25 00:13:41.651204+03
7402b898-4d2c-41d5-a3bf-92e621e44e3c	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187577862	Tag-17	Tag-17	360	1905	CW	Q1	2026-06-25 00:12:58.642486+03	2026-06-25 00:13:41.651204+03
724ad7c5-05e0-4210-babb-50a07c58dd81	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187575815	Tag-6	Tag-6	360	1905	CW	Q1	2026-06-25 00:12:58.72387+03	2026-06-25 00:13:41.651204+03
0a485826-7259-4e67-8fc6-2dfc0dca5da9	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187578887	Tag-9	Tag-9	360	1905	CW	Q1	2026-06-25 00:12:58.805062+03	2026-06-25 00:13:41.651204+03
90720c4f-3b60-43e3-b4e9-56a203c56352	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187573767	Tag-1	Tag-1	360	1905	CW	Q1	2026-06-25 00:12:58.886189+03	2026-06-25 00:13:41.651204+03
f93e2c3f-6128-4249-a300-b5cd31c0b83c	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187576838	Tag-18	Tag-18	360	1905	CW	Q1	2026-06-25 00:12:58.967674+03	2026-06-25 00:13:41.651204+03
302fb21d-cce1-4daf-822d-508d9c79010c	6d9c1e2c-7fae-4dee-977f-fbceab85db08	4187574791	Tag-5	Tag-5	360	1905	CW	Q1	2026-06-25 00:12:59.04886+03	2026-06-25 00:13:41.651204+03
\.


--
-- Data for Name: scan_reports; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.scan_reports (session_id, reader_device_id, tags_detected, scanned_at, received_at, id) FROM stdin;
b225ad05-a70d-48cb-8c29-a31adc1077fc	reader-room-101	["RFID-TAG-001", "RFID-TAG-002"]	2026-06-18 18:20:41.585217+03	2026-06-18 18:20:41.643312+03	ace1e35d-4563-4c0e-9971-030e174e807a
\.


--
-- Data for Name: seat_state_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.seat_state_history (session_id, seat_id, is_occupied, detected_at, id, created_at) FROM stdin;
6d9c1e2c-7fae-4dee-977f-fbceab85db08	1cbbf342-4bbb-4efb-980b-0ce65570c40a	t	2026-06-25 00:23:39.415506+03	c4ef2e4f-87e4-40c6-abd5-8f910bf49bee	2026-06-25 00:23:26.207383+03
6d9c1e2c-7fae-4dee-977f-fbceab85db08	e39d2ae8-e335-4a1a-bc05-d695a1aff5ce	t	2026-06-25 00:23:39.415506+03	53e91ba9-f2e2-4edd-baca-cde80a617dbf	2026-06-25 00:23:26.207383+03
6d9c1e2c-7fae-4dee-977f-fbceab85db08	f0266095-6e12-4c36-8595-89777c17b657	t	2026-06-25 00:23:39.415506+03	c629f4e7-d337-46b7-9eb4-16365de8c37e	2026-06-25 00:23:26.207383+03
6d9c1e2c-7fae-4dee-977f-fbceab85db08	9d8236a3-a614-4c3f-a4dd-7341256c76e0	t	2026-06-25 00:23:39.415506+03	ff4fa594-b165-410f-80f7-99800befbec7	2026-06-25 00:23:26.207383+03
6d9c1e2c-7fae-4dee-977f-fbceab85db08	202ca11b-bad4-4fda-8ecc-7d5e4d29b836	t	2026-06-25 00:23:39.415506+03	dd918e92-7dc8-4f9a-9918-bcd7bb8b36c9	2026-06-25 00:23:26.207383+03
6d9c1e2c-7fae-4dee-977f-fbceab85db08	3599694b-3fb9-4296-a16d-ed11d68bf474	t	2026-06-25 00:23:39.415506+03	6970c7ad-8b6d-4338-8565-c226004e7ca7	2026-06-25 00:23:26.207383+03
6d9c1e2c-7fae-4dee-977f-fbceab85db08	32627e2f-d37c-47b0-b21b-e5c354637f28	t	2026-06-25 00:23:39.415506+03	f02b8b0c-8b4f-4bc2-a171-a2c1ab51a6c6	2026-06-25 00:23:26.207383+03
6d9c1e2c-7fae-4dee-977f-fbceab85db08	19efcfd1-900f-42ca-8150-dd2ff5617d52	t	2026-06-25 00:23:39.415506+03	0750e461-9911-424f-a8ed-a4d44a9e41a3	2026-06-25 00:23:26.207383+03
6d9c1e2c-7fae-4dee-977f-fbceab85db08	4728885f-dc41-47bb-9037-586ca6d3022f	t	2026-06-25 00:23:39.415506+03	8655624c-ba10-4d6d-82e3-8313fbbb81a4	2026-06-25 00:23:26.207383+03
6d9c1e2c-7fae-4dee-977f-fbceab85db08	5a5970c5-20c7-4d8f-9e8c-9c9ee0b25682	t	2026-06-25 00:23:39.415506+03	923e392a-08b7-4bf1-8cab-a04b1a52cad0	2026-06-25 00:23:26.207383+03
\.


--
-- Data for Name: seat_states; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.seat_states (session_id, seat_id, is_occupied, last_seen_at, id) FROM stdin;
6d9c1e2c-7fae-4dee-977f-fbceab85db08	1cbbf342-4bbb-4efb-980b-0ce65570c40a	t	2026-06-25 00:13:41.666354+03	1ebb0218-dc48-44b9-970b-df713b616674
6d9c1e2c-7fae-4dee-977f-fbceab85db08	202ca11b-bad4-4fda-8ecc-7d5e4d29b836	t	2026-06-25 00:13:41.666354+03	2e78050a-424c-4ceb-a09d-83e06a15bff8
6d9c1e2c-7fae-4dee-977f-fbceab85db08	f0266095-6e12-4c36-8595-89777c17b657	t	2026-06-25 00:13:41.666354+03	3eb24c44-56eb-4555-8c13-e22c39e31c25
6d9c1e2c-7fae-4dee-977f-fbceab85db08	3599694b-3fb9-4296-a16d-ed11d68bf474	t	2026-06-25 00:13:41.666354+03	6b293b2b-c4d7-48cd-8c88-ab1d014d4931
6d9c1e2c-7fae-4dee-977f-fbceab85db08	19efcfd1-900f-42ca-8150-dd2ff5617d52	t	2026-06-25 00:13:41.666354+03	7ae5e560-d821-4f6f-8d9e-e9a8031242cc
6d9c1e2c-7fae-4dee-977f-fbceab85db08	9d8236a3-a614-4c3f-a4dd-7341256c76e0	t	2026-06-25 00:13:41.666354+03	7bb5f27c-928b-4d77-8e97-ce92e6f2561e
6d9c1e2c-7fae-4dee-977f-fbceab85db08	5a5970c5-20c7-4d8f-9e8c-9c9ee0b25682	t	2026-06-25 00:13:41.666354+03	f3fa5b0b-15cf-421e-a69a-9bb408acc60e
6d9c1e2c-7fae-4dee-977f-fbceab85db08	32627e2f-d37c-47b0-b21b-e5c354637f28	t	2026-06-25 00:13:41.666354+03	f5691044-ec1a-4c13-a894-9eb8d91b1977
6d9c1e2c-7fae-4dee-977f-fbceab85db08	4728885f-dc41-47bb-9037-586ca6d3022f	t	2026-06-25 00:13:41.666354+03	fbddda6d-423a-4005-81d2-7bfa81f9a88a
6d9c1e2c-7fae-4dee-977f-fbceab85db08	e39d2ae8-e335-4a1a-bc05-d695a1aff5ce	t	2026-06-25 00:13:41.666354+03	fc3d8140-75c7-4d83-80bb-72dd0f80084c
\.


--
-- Data for Name: seats; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.seats (classroom_id, label, "row", col, tag_id, id, x_pct, y_pct) FROM stdin;
266cd434-c3c9-4711-a566-da1216cee64c	Tag-1	0	0	4187573767	1cbbf342-4bbb-4efb-980b-0ce65570c40a	74.19	45.44
266cd434-c3c9-4711-a566-da1216cee64c	Tag-17	0	1	4187577862	e39d2ae8-e335-4a1a-bc05-d695a1aff5ce	50	17.5
266cd434-c3c9-4711-a566-da1216cee64c	Tag-18	0	2	4187576838	f0266095-6e12-4c36-8595-89777c17b657	50	17.5
266cd434-c3c9-4711-a566-da1216cee64c	Tag-2	0	3	4187571719	9d8236a3-a614-4c3f-a4dd-7341256c76e0	26.58	35.49
266cd434-c3c9-4711-a566-da1216cee64c	Tag-20	1	0	4187574790	202ca11b-bad4-4fda-8ecc-7d5e4d29b836	12.52	31.86
266cd434-c3c9-4711-a566-da1216cee64c	Tag-5	1	1	4187574791	3599694b-3fb9-4296-a16d-ed11d68bf474	27.02	27.02
266cd434-c3c9-4711-a566-da1216cee64c	Tag-6	1	2	4187575815	32627e2f-d37c-47b0-b21b-e5c354637f28	73.91	44.79
266cd434-c3c9-4711-a566-da1216cee64c	Tag-7	1	3	4187576839	19efcfd1-900f-42ca-8150-dd2ff5617d52	17.5	50
266cd434-c3c9-4711-a566-da1216cee64c	Tag-8	2	0	4187577863	4728885f-dc41-47bb-9037-586ca6d3022f	28.23	69.06
266cd434-c3c9-4711-a566-da1216cee64c	Tag-9	2	1	4187578887	5a5970c5-20c7-4d8f-9e8c-9c9ee0b25682	28.03	15.59
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (email, hashed_password, full_name, role, student_id, department_id, is_active, id, created_at) FROM stdin;
dr.smith@university.edu	$2b$12$aYbQMZLKXhPH98uT0vZBVuZBJ37wa5VOevT8fub2d6OEE/L3D7wM2	Dr. Sarah Smith	lecturer	\N	b1be98cb-4ab8-48a1-b304-294823ded71f	t	6eb805fb-6b6d-4bf6-b881-48c793bd9a73	2026-06-18 18:20:40.655734+03
alice@student.edu	$2b$12$6Y.a5lzfaLTlMNYlWv095.qoCob0NxaL2V5Wb7DMJ7zhICNfYYvAm	Alice Johnson	student	STU001	b1be98cb-4ab8-48a1-b304-294823ded71f	t	41086536-3c6e-4553-9740-46b671b935b4	2026-06-18 18:20:40.865044+03
bob@student.edu	$2b$12$C.GEQNgQtADr16rjpieFhOf9FsGlgkjN8LNvdL1751tiCLvGK1Md6	Bob Williams	student	STU002	b1be98cb-4ab8-48a1-b304-294823ded71f	t	fb9d07e7-5789-4dad-bb75-18e203a9bad5	2026-06-18 18:20:41.042809+03
hod@university.edu	$2b$12$8ZUCdlXpjkqpzNJGKLbtH.UgycJPJTQ3m50VQoOvuUd3ASLX/s5FG	Prof. Ahmed Hassan	hod	\N	b1be98cb-4ab8-48a1-b304-294823ded71f	t	b465428e-4236-4de3-9136-96fbeaec2c2c	2026-06-18 18:20:41.220473+03
dr.shawky@aast.edu	$2b$12$I4fR2YmGXHEb6GsJNMF9NuB75vUiCvsN6cuBxw1ngaKK1inZzTKOy	Dr. Shawky	lecturer	\N	b1be98cb-4ab8-48a1-b304-294823ded71f	t	26f03868-dfa5-4671-b970-d6ada84fabb7	2026-06-18 18:40:25.464213+03
hod@aast.edu	$2b$12$Vh7GKarfbTTqErF3nxW/peBgNgp5jy9bxo9nFNM1BsrQjYRUD3qFm	AAST Head of Department	hod	\N	b1be98cb-4ab8-48a1-b304-294823ded71f	t	f1ba5007-8ec8-4d83-8f9e-713a3997670e	2026-06-18 18:40:25.464213+03
admin@aast.edu	$2b$12$Qd8uXbAdR9h24WUJL4a84uHh5wC0Q7M.92aP1wYeL41UN8/ZPda7K	System Administrator	admin	\N	b1be98cb-4ab8-48a1-b304-294823ded71f	t	cb828b53-dc15-4f67-ba5b-12d1db9cae00	2026-06-18 18:40:25.464213+03
ahmedzalata@aast.edu	$2b$12$/7pR1rM7xfHwdUImgZ4diuo1bq.FKYGIgTSzAZOs7q4MF4sez/msS	Ahmed Zalata	student	221006825	b1be98cb-4ab8-48a1-b304-294823ded71f	t	8f3a62f9-14dd-4784-bb06-fa6c35c62c15	2026-06-24 15:25:07.342907+03
youssefreda@aast.edu	$2b$12$boXtNbnU8JFl20xJBuTbWOsHNhzwCPISvX0Vh89fjRE5aR/8sPbOi	Youssef Reda	student	221006826	b1be98cb-4ab8-48a1-b304-294823ded71f	t	323aa6dd-da2b-4cbe-8f43-cb5cf05d7e7f	2026-06-24 15:26:01.580827+03
alimohammed@aast.edu	$2b$12$e8LoPJc4ipuVk6MP45RaeearzACyW.gE4sjpxdN6BhdB87txDEjYG	Ali Mohammed	student	221006827	b1be98cb-4ab8-48a1-b304-294823ded71f	t	7976e276-0253-4563-b8ef-bb4be261bf73	2026-06-24 15:26:32.021667+03
amrelmaghraby@aast.edu	$2b$12$rXh6fCSt1Jan/AjZQ/bPW.eJGEeeuPZXVyV3WDnCR9BBVQtOpoQ2a	Amr Elmaghraby	student	221006829	b1be98cb-4ab8-48a1-b304-294823ded71f	t	ac340fc3-0e9f-437f-8281-3968fa0476b3	2026-06-24 15:27:58.421226+03
yehiaelmaadawy@aast.edu	$2b$12$pe8N/VBHk6676rrM/fboSOePydlQfamBYithgnHVYi6NsHM33WCom	Yehia Elmaadawy	student	221006828	b1be98cb-4ab8-48a1-b304-294823ded71f	t	0232cb03-a5d3-415f-9df9-755e10ee5477	2026-06-24 15:27:13.982181+03
\.


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: attendance_records attendance_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_records
    ADD CONSTRAINT attendance_records_pkey PRIMARY KEY (id);


--
-- Name: attendance_sessions attendance_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_sessions
    ADD CONSTRAINT attendance_sessions_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: classrooms classrooms_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.classrooms
    ADD CONSTRAINT classrooms_name_key UNIQUE (name);


--
-- Name: classrooms classrooms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.classrooms
    ADD CONSTRAINT classrooms_pkey PRIMARY KEY (id);


--
-- Name: course_classes course_classes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_classes
    ADD CONSTRAINT course_classes_pkey PRIMARY KEY (id);


--
-- Name: courses courses_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_code_key UNIQUE (code);


--
-- Name: courses courses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_pkey PRIMARY KEY (id);


--
-- Name: departments departments_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_name_key UNIQUE (name);


--
-- Name: departments departments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_pkey PRIMARY KEY (id);


--
-- Name: enrollments enrollments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_pkey PRIMARY KEY (id);


--
-- Name: rfid_readings rfid_readings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfid_readings
    ADD CONSTRAINT rfid_readings_pkey PRIMARY KEY (id);


--
-- Name: scan_reports scan_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scan_reports
    ADD CONSTRAINT scan_reports_pkey PRIMARY KEY (id);


--
-- Name: seat_state_history seat_state_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seat_state_history
    ADD CONSTRAINT seat_state_history_pkey PRIMARY KEY (id);


--
-- Name: seat_states seat_states_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seat_states
    ADD CONSTRAINT seat_states_pkey PRIMARY KEY (id);


--
-- Name: seats seats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT seats_pkey PRIMARY KEY (id);


--
-- Name: seats seats_tag_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT seats_tag_id_key UNIQUE (tag_id);


--
-- Name: attendance_records uq_attendance_session_student; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_records
    ADD CONSTRAINT uq_attendance_session_student UNIQUE (session_id, student_id);


--
-- Name: enrollments uq_enrollment_student_course_class; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT uq_enrollment_student_course_class UNIQUE (student_id, course_id, class_id);


--
-- Name: seats uq_seat_label; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT uq_seat_label UNIQUE (classroom_id, label);


--
-- Name: seats uq_seat_position; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT uq_seat_position UNIQUE (classroom_id, "row", col);


--
-- Name: seat_states uq_seat_state_session_seat; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seat_states
    ADD CONSTRAINT uq_seat_state_session_seat UNIQUE (session_id, seat_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_student_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_student_id_key UNIQUE (student_id);


--
-- Name: ix_attendance_records_session_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_attendance_records_session_status ON public.attendance_records USING btree (session_id, status);


--
-- Name: ix_audit_logs_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_session ON public.audit_logs USING btree (session_id);


--
-- Name: ix_rfid_readings_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rfid_readings_session ON public.rfid_readings USING btree (session_id);


--
-- Name: ix_rfid_readings_tag; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rfid_readings_tag ON public.rfid_readings USING btree (tag_hex_id);


--
-- Name: ix_rfid_readings_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rfid_readings_timestamp ON public.rfid_readings USING btree (detected_at);


--
-- Name: ix_scan_reports_session_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scan_reports_session_time ON public.scan_reports USING btree (session_id, scanned_at);


--
-- Name: ix_seat_state_history_session_seat_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_seat_state_history_session_seat_time ON public.seat_state_history USING btree (session_id, seat_id, detected_at);


--
-- Name: ix_seat_states_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_seat_states_session ON public.seat_states USING btree (session_id);


--
-- Name: ix_session_course_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_session_course_status ON public.attendance_sessions USING btree (course_id, status);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: attendance_records attendance_records_seat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_records
    ADD CONSTRAINT attendance_records_seat_id_fkey FOREIGN KEY (seat_id) REFERENCES public.seats(id);


--
-- Name: attendance_records attendance_records_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_records
    ADD CONSTRAINT attendance_records_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.attendance_sessions(id);


--
-- Name: attendance_records attendance_records_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_records
    ADD CONSTRAINT attendance_records_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);


--
-- Name: attendance_sessions attendance_sessions_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_sessions
    ADD CONSTRAINT attendance_sessions_class_id_fkey FOREIGN KEY (class_id) REFERENCES public.course_classes(id);


--
-- Name: attendance_sessions attendance_sessions_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_sessions
    ADD CONSTRAINT attendance_sessions_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classrooms(id);


--
-- Name: attendance_sessions attendance_sessions_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_sessions
    ADD CONSTRAINT attendance_sessions_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id);


--
-- Name: attendance_sessions attendance_sessions_lecturer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_sessions
    ADD CONSTRAINT attendance_sessions_lecturer_id_fkey FOREIGN KEY (lecturer_id) REFERENCES public.users(id);


--
-- Name: audit_logs audit_logs_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.attendance_sessions(id);


--
-- Name: classrooms classrooms_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.classrooms
    ADD CONSTRAINT classrooms_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id);


--
-- Name: course_classes course_classes_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_classes
    ADD CONSTRAINT course_classes_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classrooms(id);


--
-- Name: course_classes course_classes_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_classes
    ADD CONSTRAINT course_classes_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id);


--
-- Name: course_classes course_classes_lecturer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_classes
    ADD CONSTRAINT course_classes_lecturer_id_fkey FOREIGN KEY (lecturer_id) REFERENCES public.users(id);


--
-- Name: courses courses_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id);


--
-- Name: courses courses_lecturer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_lecturer_id_fkey FOREIGN KEY (lecturer_id) REFERENCES public.users(id);


--
-- Name: enrollments enrollments_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_class_id_fkey FOREIGN KEY (class_id) REFERENCES public.course_classes(id);


--
-- Name: enrollments enrollments_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id);


--
-- Name: enrollments enrollments_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);


--
-- Name: rfid_readings rfid_readings_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rfid_readings
    ADD CONSTRAINT rfid_readings_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.attendance_sessions(id);


--
-- Name: scan_reports scan_reports_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scan_reports
    ADD CONSTRAINT scan_reports_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.attendance_sessions(id);


--
-- Name: seat_state_history seat_state_history_seat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seat_state_history
    ADD CONSTRAINT seat_state_history_seat_id_fkey FOREIGN KEY (seat_id) REFERENCES public.seats(id);


--
-- Name: seat_state_history seat_state_history_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seat_state_history
    ADD CONSTRAINT seat_state_history_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.attendance_sessions(id);


--
-- Name: seat_states seat_states_seat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seat_states
    ADD CONSTRAINT seat_states_seat_id_fkey FOREIGN KEY (seat_id) REFERENCES public.seats(id);


--
-- Name: seat_states seat_states_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seat_states
    ADD CONSTRAINT seat_states_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.attendance_sessions(id);


--
-- Name: seats seats_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT seats_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classrooms(id);


--
-- Name: users users_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id);


--
-- PostgreSQL database dump complete
--

\unrestrict EiOuDg3EucsMLpWpuYGkSZv903Y24pURbLnK8jcLzZVieKteFVb9mLgEj98qffM

