import time
import pandas as pd

class NetworkStats:
    def __init__(self):
        self.stats = []  # Initialize an empty list to store stats

    def record_upload(self, filename, filesize, start_time, end_time):
        
        ##Record statistics for an upload operation.
        
        rate_mb_s = filesize / (end_time - start_time) / (1024 * 1024)  # MB/s
        self.stats.append({
            "operation": "upload",
            "filename": filename,
            "filesize_bytes": filesize,
            "rate_mb_s": rate_mb_s,
            "time_s": end_time - start_time
        })

    def record_download(self, filename, filesize, start_time, end_time):
        
        ##Record statistics for a download operation.
        
        rate_mb_s = filesize / (end_time - start_time) / (1024 * 1024)  # MB/s
        self.stats.append({
            "operation": "download",
            "filename": filename,
            "filesize_bytes": filesize,
            "rate_mb_s": rate_mb_s,
            "time_s": end_time - start_time
        })

    def record_response_time(self, command, start_time, end_time, filename=None, filesize=None):
        
        ##Record response time for a specific command.
        ##Optional parameters `filename` and `filesize` can provide additional context.
        
        response_time_ms = (end_time - start_time) * 1000  # ms
        stat = {
            "operation": "response",
            "command": command,
            "response_time_ms": response_time_ms,
        }
        if filename:
            stat["filename"] = filename
        if filesize:
            stat["filesize_bytes"] = filesize
        self.stats.append(stat)

    def save_stats_to_csv(self, filepath):
        
        ##Save all recorded statistics to a CSV file.
        
        # Convert the stats list to a DataFrame and save it as a CSV
        stats_df = pd.DataFrame(self.stats)
        stats_df.to_csv(filepath, index=False)
        print(f"[INFO] Stats saved to {filepath}")
