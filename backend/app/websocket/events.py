# app/websocket/events.py
# All WebSocket event type constants used in the system

class Events:
    # Officer events
    OFFICER_ONLINE = "officer.online"
    OFFICER_OFFLINE = "officer.offline"
    OFFICER_LOCATION = "officer.location"

    # Incident events
    INCIDENT_NEW = "incident.new"
    INCIDENT_UPDATED = "incident.updated"
    INCIDENT_PRIORITY = "incident.priority"

    # Pursuit events
    SUSPECT_LOCATED = "suspect.located"
    SUSPECT_LOST = "suspect.lost"
    PURSUIT_ROUTE = "pursuit.route"
    INTERCEPTION_POINT = "interception.point"

    # CCTV events
    CCTV_MATCH = "cctv.match"
    CCTV_FRAME = "cctv.frame"

    # Missing person events
    MISSING_PERSON_SEARCH_STARTED = "missing.search.started"
    MISSING_PERSON_FOUND = "missing.person.found"
    MISSING_PERSON_NOT_FOUND = "missing.person.notfound"

    # Intelligence events
    INTELLIGENCE_RESULT = "intelligence.result"
    OFFENDER_MATCH = "offender.match"

    # Escalation events
    ESCALATION_TRIGGERED = "escalation.triggered"
    SUPERVISOR_NOTIFIED = "supervisor.notified"

    # Coordination events (Feature 5)
    ROLE_ASSIGNED = "role.assigned"
    INCIDENT_ALERT = "incident.alert"

    # Report events (Feature 6)
    REPORT_GENERATED = "report.generated"