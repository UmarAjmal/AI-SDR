import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Calendar,
  Clock,
  ExternalLink,
  CheckCircle2,
  Copy,
  Check,
  RefreshCw,
  Plus,
} from 'lucide-react';
import { FrostedGlassCard } from './ui/FrostedGlassCard';
import { SquircleButton } from './ui/SquircleButton';
import { SquircleInput } from './ui/SquircleInput';
import { SquircleModal } from './ui/SquircleModal';

interface AppointmentItem {
  id: string;
  title: string;
  attendee_name?: string;
  attendee_email: string;
  company_name?: string;
  host_email: string;
  start_time: string;
  end_time: string;
  prospect_timezone?: string;
  status: 'CONFIRMED' | 'CANCELLED' | 'RESCHEDULED';
  meeting_link?: string;
  provider?: string;
}

interface ProposalSlot {
  id?: string;
  formatted_prospect?: string;
  formatted_host?: string;
  start_iso?: string;
  end_iso?: string;
  start_time?: string;
  end_time?: string;
}

export const CalendarView: React.FC = () => {
  const [appointments, setAppointments] = useState<AppointmentItem[]>([]);
  const [connections, setConnections] = useState<any[]>([]);
  const [proposedSlots, setProposedSlots] = useState<ProposalSlot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [prospectTz, setProspectTz] = useState('America/New_York');

  // Slot proposal state
  const [isLoadingSlots, setIsLoadingSlots] = useState(false);
  const [copiedSlotId, setCopiedSlotId] = useState<string | null>(null);

  // Manual Booking Modal
  const [isBookingOpen, setIsBookingOpen] = useState(false);
  const [selectedSlotForBooking, setSelectedSlotForBooking] = useState<ProposalSlot | null>(null);
  const [bookingProspectName, setBookingProspectName] = useState('');
  const [bookingProspectEmail, setBookingProspectEmail] = useState('');
  const [bookingTitle, setBookingTitle] = useState('Codenter AI SDR Platform Demo');
  const [isBooking, setIsBooking] = useState(false);
  const [bookingNotice, setBookingNotice] = useState<string | null>(null);

  // Load calendar appointments and connections
  const fetchCalendarData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [apptsRes, connsRes] = await Promise.allSettled([
        axios.get('/api/v1/calendar/appointments'),
        axios.get('/api/v1/calendar/connections'),
      ]);

      if (apptsRes.status === 'fulfilled') {
        const raw = apptsRes.value.data || [];
        setAppointments(
          raw.map((a: any) => ({
            id: a.id,
            title: a.title || 'Discovery Call',
            attendee_name: a.attendee_name || a.attendee_email?.split('@')[0] || 'Prospect',
            attendee_email: a.attendee_email || '',
            company_name: a.company_name || 'Enterprise Account',
            host_email: a.host_email || 'sdr@workspace.com',
            start_time: a.start_time,
            end_time: a.end_time,
            prospect_timezone: a.prospect_timezone || 'UTC',
            status: a.status || 'CONFIRMED',
            meeting_link: a.meeting_link || 'https://meet.google.com',
            provider: a.calendar_connection_id ? 'CALENDAR_SYNC' : 'GOOGLE',
          }))
        );
      } else {
        setAppointments([]);
      }

      if (connsRes.status === 'fulfilled') {
        setConnections(connsRes.value.data || []);
      }
    } catch (err) {
      console.error('Failed to load calendar data:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCalendarData();
  }, [fetchCalendarData]);

  // Propose Slots based on prospect timezone
  const fetchProposedSlots = useCallback(async () => {
    setIsLoadingSlots(true);
    try {
      const res = await axios.get('/api/v1/calendar/propose-slots', {
        params: { prospect_timezone: prospectTz },
      });
      const rawSlots = res.data || [];
      setProposedSlots(
        rawSlots.map((s: any, idx: number) => ({
          id: `slot-${idx}`,
          formatted_prospect: s.formatted_prospect || `${new Date(s.start_time || s.start_iso).toLocaleString()} (${prospectTz})`,
          formatted_host: s.formatted_host || new Date(s.start_time || s.start_iso).toLocaleTimeString(),
          start_iso: s.start_time || s.start_iso,
          end_iso: s.end_time || s.end_iso,
        }))
      );
    } catch (err) {
      // If no calendar connection active yet, handle gracefully
      setProposedSlots([]);
    } finally {
      setIsLoadingSlots(false);
    }
  }, [prospectTz]);

  useEffect(() => {
    if (connections.length > 0) {
      fetchProposedSlots();
    }
  }, [connections, fetchProposedSlots]);

  const handleCopySnippet = (slot: ProposalSlot) => {
    const text = `Would ${slot.formatted_prospect || slot.start_iso} work for a brief 15-minute discovery call?`;
    navigator.clipboard.writeText(text);
    setCopiedSlotId(slot.id || 'copied');
    setTimeout(() => setCopiedSlotId(null), 2000);
  };

  const handleConfirmBooking = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bookingProspectEmail.trim()) return;

    setIsBooking(true);
    try {
      const activeConn = connections[0];
      await axios.post('/api/v1/calendar/book', {
        connection_id: activeConn?.id || 'conn-default',
        lead_id: 'manual-booking',
        title: bookingTitle,
        start_time: selectedSlotForBooking?.start_iso || new Date().toISOString(),
        end_time: selectedSlotForBooking?.end_iso || new Date(Date.now() + 30 * 60000).toISOString(),
        attendee_email: bookingProspectEmail.trim().toLowerCase(),
        host_email: activeConn?.account_email || 'alex.vance@codenter.ai',
        prospect_timezone: prospectTz,
      });

      setBookingNotice('Meeting booked and confirmed! Concurrency lock acquired and calendar invite dispatched.');
      setIsBookingOpen(false);
      setBookingProspectEmail('');
      setBookingProspectName('');
      await fetchCalendarData();
    } catch (err: any) {
      setBookingNotice(err.response?.data?.detail || 'Booking failed. Slot may no longer be available.');
    } finally {
      setIsBooking(false);
      setTimeout(() => setBookingNotice(null), 5000);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[var(--text-primary)] flex items-center gap-2">
            Autonomous Calendar &amp; Meeting Booking
            <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              Concurrency-Safe Locking
            </span>
          </h2>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Section 10 Meeting Booking: Auto-stop sequence on confirmation, dynamic prospect timezone conversion, and 15-min buffers.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-xs text-[var(--text-muted)] font-medium p-2 px-3 rounded-[12px] bg-white/70 border border-white/80">
            Connected Hosts:{' '}
            <span className="font-bold text-slate-800">{connections.length} Active</span>
          </div>

          <button
            onClick={fetchCalendarData}
            className="p-2 rounded-[12px] bg-white/80 border border-slate-200 hover:bg-white text-slate-600 hover:text-slate-900 transition-all"
            title="Refresh Calendar"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Notice Banner */}
      {bookingNotice && (
        <FrostedGlassCard className="p-3.5 border-emerald-200/80 bg-emerald-50/60 text-xs text-emerald-800 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            {bookingNotice}
          </span>
          <button onClick={() => setBookingNotice(null)} className="text-emerald-500 hover:text-emerald-700 font-bold">
            ✕
          </button>
        </FrostedGlassCard>
      )}

      {/* Loading Skeleton */}
      {isLoading ? (
        <FrostedGlassCard elevated className="p-16 flex flex-col items-center justify-center text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-[var(--accent-primary)] animate-spin" />
          <div className="text-sm font-semibold text-[var(--text-primary)]">Syncing Scheduled Appointments...</div>
          <div className="text-xs text-[var(--text-muted)]">Verifying provider event confirmations and timezone locks</div>
        </FrostedGlassCard>
      ) : appointments.length === 0 ? (
        /* Pristine 3D Frosted Glass Empty State */
        <FrostedGlassCard elevated className="p-12 md:p-16 flex flex-col items-center justify-center text-center space-y-5">
          <div className="w-16 h-16 rounded-[24px] bg-[var(--accent-subtle)] border border-[var(--accent-border)] flex items-center justify-center text-[var(--accent-primary)] shadow-sm">
            <Calendar className="w-8 h-8" />
          </div>
          <div className="max-w-md space-y-1.5">
            <h3 className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
              No Meetings Scheduled Yet
            </h3>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              When prospect replies request a demo or calendar invite, the AI SDR autonomously resolves free/busy availability and locks slots into verified bookings here.
            </p>
          </div>
          <SquircleButton
            variant="primary"
            size="md"
            onClick={() => {
              setSelectedSlotForBooking(null);
              setIsBookingOpen(true);
            }}
            className="flex items-center gap-2 shadow-md"
          >
            <Plus className="w-4 h-4" />
            Schedule Demo Meeting
          </SquircleButton>
        </FrostedGlassCard>
      ) : (
        /* Render Confirmed Appointments */
        <div className="space-y-6">
          <FrostedGlassCard elevated className="p-0 overflow-hidden">
            <div className="p-4 border-b border-white/60 bg-white/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-[var(--accent-primary)]" />
                <h3 className="text-sm font-bold text-[var(--text-primary)]">
                  Confirmed Appointments ({appointments.length})
                </h3>
              </div>
              <SquircleButton
                variant="primary"
                size="sm"
                onClick={() => {
                  setSelectedSlotForBooking(null);
                  setIsBookingOpen(true);
                }}
                className="flex items-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                Book Meeting
              </SquircleButton>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="border-b border-white/60 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] bg-white/20">
                    <th className="py-3 px-6">Meeting &amp; Prospect</th>
                    <th className="py-3 px-6">Start Time</th>
                    <th className="py-3 px-6">Host Email</th>
                    <th className="py-3 px-6 text-center">Timezone</th>
                    <th className="py-3 px-6 text-center">Status</th>
                    <th className="py-3 px-6 text-right">Meeting Link</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/60">
                  {appointments.map((a) => (
                    <tr key={a.id} className="hover:bg-white/40 transition-colors">
                      <td className="py-3.5 px-6">
                        <div className="font-semibold text-[var(--text-primary)]">{a.title}</div>
                        <div className="text-xs text-[var(--text-muted)] mt-0.5">
                          {a.attendee_name} ({a.attendee_email})
                        </div>
                      </td>
                      <td className="py-3.5 px-6 text-xs font-medium text-slate-700">
                        {new Date(a.start_time).toLocaleString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="py-3.5 px-6 text-xs text-slate-500">{a.host_email}</td>
                      <td className="py-3.5 px-6 text-center text-xs text-slate-500 font-mono">
                        {a.prospect_timezone}
                      </td>
                      <td className="py-3.5 px-6 text-center">
                        <span className="px-2.5 py-1 rounded-[10px] text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {a.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-6 text-right">
                        {a.meeting_link ? (
                          <a
                            href={a.meeting_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline font-medium"
                          >
                            Join Call <ExternalLink className="w-3 h-3" />
                          </a>
                        ) : (
                          <span className="text-xs text-slate-400">Generated upon sync</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </FrostedGlassCard>
        </div>
      )}

      {/* Dynamic Propose Slots Tool */}
      <FrostedGlassCard className="p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Clock className="w-4 h-4 text-[var(--accent-primary)]" />
              Dynamic Slot Calculation &amp; Timezone Converter
            </h3>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Section 10.1: Convert available host slots into prospect local time with 15-minute buffers.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-medium">Prospect Timezone:</span>
            <select
              value={prospectTz}
              onChange={(e) => setProspectTz(e.target.value)}
              className="text-xs bg-white/80 border border-slate-200 rounded-[12px] px-3 py-1.5 font-medium text-slate-700"
            >
              <option value="America/New_York">Eastern (EDT / New York)</option>
              <option value="America/Chicago">Central (CDT / Chicago)</option>
              <option value="America/Denver">Mountain (MDT / Denver)</option>
              <option value="America/Los_Angeles">Pacific (PDT / Los Angeles)</option>
              <option value="Europe/London">London (BST / GMT)</option>
              <option value="Asia/Karachi">Pakistan (PKT / Karachi)</option>
            </select>
          </div>
        </div>

        {connections.length === 0 ? (
          <div className="p-4 rounded-[14px] bg-amber-50/60 border border-amber-200 text-xs text-amber-800">
            No calendar provider connected yet. Connect Google Calendar or Microsoft Outlook in the Integrations tab to calculate real-time free/busy slots.
          </div>
        ) : proposedSlots.length === 0 ? (
          <div className="p-4 rounded-[14px] bg-slate-50 border border-slate-200/60 text-xs text-slate-600 text-center">
            {isLoadingSlots ? 'Calculating available slots...' : 'No available slots found within working hours.'}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
            {proposedSlots.map((slot) => (
              <div
                key={slot.id}
                className="p-3.5 rounded-[16px] bg-white/70 border border-white/80 shadow-xs flex items-center justify-between"
              >
                <div className="space-y-0.5">
                  <p className="text-xs font-bold text-slate-800">{slot.formatted_prospect}</p>
                  <p className="text-[10px] text-slate-500">Host: {slot.formatted_host}</p>
                </div>
                <button
                  onClick={() => handleCopySnippet(slot)}
                  className="p-1.5 rounded-[8px] hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-all"
                  title="Copy snippet"
                >
                  {copiedSlotId === slot.id ? (
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            ))}
          </div>
        )}
      </FrostedGlassCard>

      {/* Manual Booking Modal */}
      <SquircleModal
        isOpen={isBookingOpen}
        onClose={() => setIsBookingOpen(false)}
        title="Schedule Demo Meeting"
        maxWidth="md"
      >
        <form onSubmit={handleConfirmBooking} className="space-y-4 pt-1">
          <SquircleInput
            label="Meeting Title"
            value={bookingTitle}
            onChange={(e) => setBookingTitle(e.target.value)}
            required
          />

          <SquircleInput
            label="Prospect Name"
            value={bookingProspectName}
            onChange={(e) => setBookingProspectName(e.target.value)}
            placeholder="e.g. Marcus Vance"
          />

          <SquircleInput
            label="Prospect Email *"
            type="email"
            value={bookingProspectEmail}
            onChange={(e) => setBookingProspectEmail(e.target.value)}
            placeholder="marcus@company.com"
            required
          />

          <div className="pt-3 flex justify-end gap-3">
            <SquircleButton
              variant="outline"
              type="button"
              onClick={() => setIsBookingOpen(false)}
            >
              Cancel
            </SquircleButton>
            <SquircleButton
              variant="primary"
              type="submit"
              isLoading={isBooking}
            >
              Lock Slot &amp; Confirm
            </SquircleButton>
          </div>
        </form>
      </SquircleModal>
    </div>
  );
};
