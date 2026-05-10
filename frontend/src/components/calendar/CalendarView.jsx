import { useState, useEffect } from "react";
import { api } from "../../services/api";

function EventCard({ event }) {
  const start = event.start ? new Date(event.start) : null;
  const isToday = start && start.toDateString() === new Date().toDateString();
  const isPast  = start && start < new Date();

  return (
    <div className={`glass rounded-xl p-4 border transition-all ${
      isToday ? "border-blue-500/40 bg-blue-500/5" :
      isPast  ? "border-white/5 opacity-60" :
      "border-white/5 hover:border-white/10"
    }`}>
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-white text-sm truncate">{event.summary}</p>
          {event.description && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{event.description}</p>
          )}
        </div>
        {isToday && (
          <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/20 flex-shrink-0">Today</span>
        )}
      </div>
      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
        {start && <span>🕐 {start.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>}
        {event.attendees?.length > 0 && <span>👥 {event.attendees.length} attendee{event.attendees.length > 1 ? "s" : ""}</span>}
      </div>
      {event.attendees?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {event.attendees.slice(0, 3).map(e => (
            <span key={e} className="text-xs px-1.5 py-0.5 rounded bg-white/5 text-gray-400">{e}</span>
          ))}
          {event.attendees.length > 3 && <span className="text-xs text-gray-500">+{event.attendees.length - 3}</span>}
        </div>
      )}
    </div>
  );
}

export default function CalendarView() {
  const [events, setEvents] = useState([]);
  const [calendars, setCalendars] = useState([]);
  const [oauthStatus, setOauthStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [daysAhead, setDaysAhead] = useState(7);
  const [showAddEvent, setShowAddEvent] = useState(false);
  const [showScheduleMeeting, setShowScheduleMeeting] = useState(false);
  const [newEvent, setNewEvent] = useState({ summary: "", description: "", start: "", end: "", attendees: "" });
  const [meeting, setMeeting] = useState({ lead_email: "", lead_name: "", company: "", service: "AI automation" });

  useEffect(() => {
    loadAll();
  }, [daysAhead]);

  async function loadAll() {
    setLoading(true);
    try {
      const [ev, cals, auth] = await Promise.all([
        api.get(`/api/v1/calendar/events?days_ahead=${daysAhead}`).then(r => r.data).catch(() => []),
        api.get("/api/v1/calendar/calendars").then(r => r.data).catch(() => []),
        api.get("/api/v1/auth/gmail/status").then(r => r.data).catch(() => null),
      ]);
      setEvents(ev);
      setCalendars(cals);
      setOauthStatus(auth);
    } catch (e) { console.error(e); }
    setLoading(false);
  }

  async function addEvent() {
    try {
      const body = {
        summary: newEvent.summary,
        description: newEvent.description,
        start: newEvent.start || undefined,
        end: newEvent.end || undefined,
        attendees: newEvent.attendees ? newEvent.attendees.split(",").map(e => e.trim()).filter(Boolean) : [],
      };
      await api.post("/api/v1/calendar/events", body);
      setShowAddEvent(false);
      setNewEvent({ summary: "", description: "", start: "", end: "", attendees: "" });
      loadAll();
    } catch (e) { alert(`Error: ${e.response?.data?.detail || e.message}`); }
  }

  async function scheduleMeeting() {
    try {
      await api.post("/api/v1/calendar/meetings/schedule", meeting);
      setShowScheduleMeeting(false);
      loadAll();
    } catch (e) { alert(`Error: ${e.response?.data?.detail || e.message}`); }
  }

  const todayEvents = events.filter(e => e.start && new Date(e.start).toDateString() === new Date().toDateString());
  const upcomingEvents = events.filter(e => e.start && new Date(e.start) > new Date());

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Calendar</h1>
          <p className="text-gray-400 text-sm">Google Calendar integration</p>
        </div>
        <div className="flex gap-2 items-center">
          <select value={daysAhead} onChange={e => setDaysAhead(Number(e.target.value))}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none">
            {[7, 14, 30].map(d => <option key={d} value={d}>Next {d} days</option>)}
          </select>
          <button onClick={() => setShowScheduleMeeting(true)}
            className="px-4 py-2 border border-blue-500/30 text-blue-400 hover:bg-blue-500/10 rounded-lg text-sm transition-colors">
            Schedule Meeting
          </button>
          <button onClick={() => setShowAddEvent(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">
            + Add Event
          </button>
        </div>
      </div>

      {/* OAuth Status Banner */}
      {oauthStatus && !oauthStatus.connected && (
        <div className="glass rounded-xl p-4 border border-yellow-500/30 bg-yellow-500/5">
          <p className="text-yellow-400 text-sm font-medium">Google Calendar not connected</p>
          <p className="text-gray-400 text-xs mt-1">
            {oauthStatus.oauth_configured
              ? "Complete Gmail OAuth to enable Calendar — go to Settings and click Connect Gmail."
              : "Add GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET to .env to enable OAuth."}
          </p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass rounded-xl p-4 border border-white/5">
          <p className="text-gray-400 text-xs mb-1">Today</p>
          <p className="text-2xl font-bold text-blue-400">{todayEvents.length}</p>
        </div>
        <div className="glass rounded-xl p-4 border border-white/5">
          <p className="text-gray-400 text-xs mb-1">Upcoming</p>
          <p className="text-2xl font-bold text-white">{upcomingEvents.length}</p>
        </div>
        <div className="glass rounded-xl p-4 border border-white/5">
          <p className="text-gray-400 text-xs mb-1">Calendars</p>
          <p className="text-2xl font-bold text-purple-400">{calendars.length}</p>
        </div>
      </div>

      {/* Events */}
      {loading ? (
        <div className="text-center text-gray-500 py-12">Loading calendar...</div>
      ) : events.length === 0 ? (
        <div className="text-center text-gray-500 py-12">
          <p>No events in the next {daysAhead} days.</p>
          <p className="text-sm mt-1">
            {oauthStatus?.connected ? "Your calendar is empty." : "Connect Google Calendar to see events."}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {events.map(event => <EventCard key={event.id} event={event} />)}
        </div>
      )}

      {/* Add Event Modal */}
      {showAddEvent && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setShowAddEvent(false)}>
          <div className="glass rounded-2xl border border-white/10 p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-white mb-4">New Event</h2>
            <div className="space-y-3">
              {[
                { key: "summary", placeholder: "Event title *" },
                { key: "description", placeholder: "Description" },
                { key: "start", placeholder: "Start (leave empty for +1h)", type: "datetime-local" },
                { key: "end", placeholder: "End (leave empty for +2h)", type: "datetime-local" },
                { key: "attendees", placeholder: "Attendees (comma-separated emails)" },
              ].map(f => (
                <input key={f.key} type={f.type || "text"} value={newEvent[f.key]}
                  onChange={e => setNewEvent(p => ({ ...p, [f.key]: e.target.value }))}
                  placeholder={f.placeholder}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50" />
              ))}
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowAddEvent(false)} className="flex-1 py-2 rounded-lg border border-white/10 text-gray-400 text-sm">Cancel</button>
              <button onClick={addEvent} disabled={!newEvent.summary} className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white text-sm font-medium">Create Event</button>
            </div>
          </div>
        </div>
      )}

      {/* Schedule Meeting Modal */}
      {showScheduleMeeting && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setShowScheduleMeeting(false)}>
          <div className="glass rounded-2xl border border-white/10 p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-white mb-1">Schedule Lead Meeting</h2>
            <p className="text-gray-500 text-xs mb-4">JARVIS will create a calendar event for the next available business day at 10 AM UTC.</p>
            <div className="space-y-3">
              {[
                { key: "lead_email", placeholder: "Lead email *" },
                { key: "lead_name", placeholder: "Lead name *" },
                { key: "company", placeholder: "Company *" },
                { key: "service", placeholder: "Service offered" },
              ].map(f => (
                <input key={f.key} value={meeting[f.key]} onChange={e => setMeeting(p => ({ ...p, [f.key]: e.target.value }))}
                  placeholder={f.placeholder}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500/50" />
              ))}
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowScheduleMeeting(false)} className="flex-1 py-2 rounded-lg border border-white/10 text-gray-400 text-sm">Cancel</button>
              <button onClick={scheduleMeeting} disabled={!meeting.lead_email || !meeting.lead_name || !meeting.company}
                className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white text-sm font-medium">Schedule</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
