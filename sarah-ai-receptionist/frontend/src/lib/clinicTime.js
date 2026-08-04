import { useEffect, useState } from "react";
import { dashboardApi } from "../services/api";

// Timestamps arrive as UTC. Rendering them with the browser's zone is only
// correct while staff sit inside the clinic — an owner checking from another
// state, or a manager covering two locations, would read the wrong hour and
// tell a patient the wrong time. The clinic's own timezone is authoritative.

// Shared across pages so mounting Appointments and Call Log doesn't fetch
// settings twice.
let settingsPromise = null;

function fetchClinicTimezone() {
  if (!settingsPromise) {
    settingsPromise = dashboardApi
      .getSettings()
      .then(({ data }) => data.timezone || null)
      .catch(() => null); // fall back to browser zone rather than blocking the page
  }
  return settingsPromise;
}

/** Clears the cache so a timezone change in Settings takes effect immediately. */
export function resetClinicTimezoneCache() {
  settingsPromise = null;
}

export function useClinicTimezone() {
  const [timeZone, setTimeZone] = useState(null);

  useEffect(() => {
    let active = true;
    fetchClinicTimezone().then((tz) => {
      if (active) setTimeZone(tz);
    });
    return () => {
      active = false;
    };
  }, []);

  return timeZone;
}

const DATE_TIME = { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" };

/**
 * Formats a UTC timestamp in the clinic's timezone.
 * Falls back to the browser's zone when the clinic's is unknown or invalid,
 * so a bad value degrades to today's behavior instead of an empty cell.
 */
export function formatInClinicZone(value, timeZone, options = DATE_TIME) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  try {
    return new Intl.DateTimeFormat("en-US", timeZone ? { ...options, timeZone } : options).format(date);
  } catch {
    return new Intl.DateTimeFormat("en-US", options).format(date);
  }
}

/** Short zone label ("EDT") so staff can see which clock they're reading. */
export function clinicZoneLabel(timeZone) {
  if (!timeZone) return "";
  try {
    const part = new Intl.DateTimeFormat("en-US", { timeZone, timeZoneName: "short" })
      .formatToParts(new Date())
      .find((p) => p.type === "timeZoneName");
    return part ? part.value : "";
  } catch {
    return "";
  }
}
