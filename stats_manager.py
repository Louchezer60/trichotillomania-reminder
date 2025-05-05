import json
import time
from typing import Dict, List
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import tkinter as tk
from tkinter import ttk

class PullingStats:
    """Tracks statistics on hair-pulling incidents."""
    
    def __init__(self):
        self.triggers: List[float] = []
        self.daily_stats: Dict[str, int] = {}
        self.load_stats()
    
    def add_trigger(self) -> None:
        """Record a new hair-pulling trigger event."""
        now = time.time()
        self.triggers.append(now)
        self.update_daily_stats()
        self.save_stats()
    
    def update_daily_stats(self) -> None:
        """Update daily statistics based on triggers."""
        today = time.strftime("%Y-%m-%d")
        if today not in self.daily_stats:
            self.daily_stats[today] = 0
        self.daily_stats[today] += 1
    
    def get_daily_report(self) -> str:
        """Get a report of today's triggers."""
        today = time.strftime("%Y-%m-%d")
        return f"Today's triggers: {self.daily_stats.get(today, 0)}"
    
    def get_weekly_stats(self) -> Dict[str, int]:
        """Get trigger counts for the past 7 days."""
        weekly_stats = {}
        today = datetime.now().date()
        for i in range(7):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            weekly_stats[date_str] = self.daily_stats.get(date_str, 0)
        return weekly_stats
    
    def get_hourly_distribution(self) -> Dict[int, int]:
        """Get distribution of triggers by hour of day."""
        hourly_stats = {hour: 0 for hour in range(24)}
        for trigger in self.triggers:
            hour = datetime.fromtimestamp(trigger).hour
            hourly_stats[hour] += 1
        return hourly_stats
    
    def load_stats(self) -> None:
        """Load stats from storage."""
        try:
            with open('hair_stats.json', 'r') as f:
                data = json.load(f)
                self.daily_stats = data.get('daily_stats', {})
                self.triggers = data.get('triggers', [])
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    
    def save_stats(self) -> None:
        """Save stats to storage."""
        data = {
            'daily_stats': self.daily_stats,
            'triggers': self.triggers
        }
        with open('hair_stats.json', 'w') as f:
            json.dump(data, f)

class StatsGraphManager:
    """Manages graphical visualization of hair-pulling statistics."""
    
    def __init__(self, stats: PullingStats, parent_frame: ttk.Frame):
        self.stats = stats
        self.parent_frame = parent_frame
        self.daily_figure = None
        self.daily_canvas = None
        self.hourly_figure = None
        self.hourly_canvas = None
        
        self._setup_graphs()
    
    def _setup_graphs(self) -> None:
        """Set up the graph frames and initial figures."""
        daily_frame = ttk.LabelFrame(self.parent_frame, text="Daily Triggers Trend")
        daily_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.daily_figure = Figure(figsize=(5, 3), dpi=100)
        self.daily_canvas = FigureCanvasTkAgg(self.daily_figure, daily_frame)
        self.daily_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        hourly_frame = ttk.LabelFrame(self.parent_frame, text="Hourly Triggers Distribution")
        hourly_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.hourly_figure = Figure(figsize=(5, 3), dpi=100)
        self.hourly_canvas = FigureCanvasTkAgg(self.hourly_figure, hourly_frame)
        self.hourly_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.update_graphs()
    
    def update_graphs(self) -> None:
        """Update both graphs with latest data."""
        self._update_daily_graph()
        self._update_hourly_graph()
    
    def _update_daily_graph(self) -> None:
        """Update the daily trend graph."""
        self.daily_figure.clear()
        ax = self.daily_figure.add_subplot(111)
        
        weekly_stats = self.stats.get_weekly_stats()
        dates = sorted(weekly_stats.keys())
        values = [weekly_stats[date] for date in dates]
        datetime_dates = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
        
        ax.bar(datetime_dates, values, color='skyblue', edgecolor='navy')
        ax.set_title('Daily Triggers (Past Week)')
        ax.set_ylabel('Number of Triggers')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator())
        self.daily_figure.autofmt_xdate()
        
        for i, v in enumerate(values):
            ax.text(i, v + 0.1, str(v), ha='center')
        
        self.daily_canvas.draw()
    
    def _update_hourly_graph(self) -> None:
        """Update the hourly distribution graph."""
        self.hourly_figure.clear()
        ax = self.hourly_figure.add_subplot(111)
        
        hourly_stats = self.stats.get_hourly_distribution()
        hours = list(range(24))
        counts = [hourly_stats.get(hour, 0) for hour in hours]
        
        ax.bar(hours, counts, color='lightgreen', edgecolor='darkgreen')
        ax.set_title('Hourly Trigger Distribution')
        ax.set_xlabel('Hour of Day (24-hour format)')
        ax.set_ylabel('Total Triggers')
        ax.set_xticks(list(range(0, 24, 2)))
        
        hour_labels = []
        for h in range(0, 24, 2):
            if h == 0:
                hour_labels.append("12 AM")
            elif h < 12:
                hour_labels.append(f"{h} AM")
            elif h == 12:
                hour_labels.append("12 PM")
            else:
                hour_labels.append(f"{h-12} PM")
        
        ax.set_xticklabels(hour_labels, rotation=45)  # Rotate labels for better fit
        
        # Adjust layout to provide more space for x-axis labels
        self.hourly_figure.subplots_adjust(bottom=0.25, left=0.15, right=0.85, top=0.85)
        
        if counts:
            max_hour = hours[counts.index(max(counts))]
            max_count = max(counts)
            if max_count > 0:
                time_str = f"{max_hour}:00" if max_hour < 12 else f"{max_hour-12 if max_hour > 12 else max_hour}:00 {'AM' if max_hour < 12 else 'PM'}"
                ax.annotate(f"Peak: {time_str}\n({max_count} triggers)",
                        xy=(max_hour, max_count),
                        xytext=(max_hour, max_count + max(counts) * 0.2),
                        arrowprops=dict(arrowstyle="->", color="red"),
                        ha='center')
        
        self.hourly_canvas.draw()