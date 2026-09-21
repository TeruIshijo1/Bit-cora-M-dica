using System;
using System.Collections.Generic;
using System.Threading;
using System.Web.Script.Serialization;
using System.Security.Cryptography;
using System.Text;
using DPUruNet;

// One isolated SDK operation over private stdio. Never writes biometric files/logs.
internal static class CaptureBridge
{
    static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 2000000 };
    static void Reply(object value) { Console.WriteLine(Json.Serialize(value)); Console.Out.Flush(); }
    static void Require(bool ok, string code) { if (!ok) throw new InvalidOperationException(code); }
    static void Clear(byte[] value) { if (value != null) Array.Clear(value, 0, value.Length); }
    static string DeviceId(Reader reader) {
        using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(reader.Description.Name))).Replace("-", "").ToLowerInvariant();
    }
    static void ClearImage(Fid image) {
        if (image == null) return;
        foreach (var view in image.Views) { Clear(view.RawImage); Clear(view.Bytes); }
        Clear(image.Bytes);
    }
    static object Capture(Dictionary<string, object> command, bool probe) {
        bool owns = false;
        using (var mutex = new Mutex(false, @"Local\HES.DigitalPersona.Capture")) {
            try {
                try { owns = mutex.WaitOne(0); } catch (AbandonedMutexException) { owns = true; }
                Require(owns, "READER_BUSY");
                using (var readers = ReaderCollection.GetReaders()) {
                    Require(readers.Count == 1, readers.Count == 0 ? "READER_DISCONNECTED" : "READER_SELECTION_REQUIRED");
                    var reader = readers[0];
                    var id = DeviceId(reader);
                    Require(reader.Open(Constants.CapturePriority.DP_PRIORITY_EXCLUSIVE) == Constants.ResultCode.DP_SUCCESS, "READER_OPEN_FAILED");
                    Require(reader.GetStatus() == Constants.ResultCode.DP_SUCCESS, "READER_DISCONNECTED");
                    Require(reader.Status.Status == Constants.ReaderStatuses.DP_STATUS_READY, "READER_NOT_READY");
                    Require(reader.Capabilities.CanCapture && reader.Capabilities.Resolutions.Length > 0, "CAPTURE_UNSUPPORTED");
                    if (probe) return new { ok = true, device_id = id, can_capture = true, sdk = "DPUruNet", cleanup = true };
                    int timeout = Convert.ToInt32(command["timeout_ms"]);
                    Require(timeout > 0 && timeout <= 120000, "CAPTURE_TIMEOUT");
                    var cancel = new Thread(() => { try { if (Console.ReadLine() == "CANCEL") reader.CancelCapture(); } catch { } });
                    cancel.IsBackground = true;
                    cancel.Start();
                    CaptureResult captured = null;
                    Fmd fmd = null;
                    try {
                        string started = DateTime.UtcNow.ToString("o");
                        Reply(new { event_type = "waiting_for_finger", device_id = id });
                        captured = reader.Capture(Constants.Formats.Fid.ANSI, Constants.CaptureProcessing.DP_IMG_PROC_DEFAULT, timeout, reader.Capabilities.Resolutions[0]);
                        string capturedAt = DateTime.UtcNow.ToString("o");
                        Require(captured != null, "CAPTURE_FAILED");
                        Require(captured.Quality != Constants.CaptureQuality.DP_QUALITY_TIMED_OUT, "CAPTURE_TIMEOUT");
                        Require(captured.Quality != Constants.CaptureQuality.DP_QUALITY_CANCELED, "CAPTURE_CANCELLED");
                        Require(captured.ResultCode == Constants.ResultCode.DP_SUCCESS && captured.Quality == Constants.CaptureQuality.DP_QUALITY_GOOD && captured.Data != null, "CAPTURE_FAILED");
                        Require(reader.GetStatus() == Constants.ResultCode.DP_SUCCESS && DeviceId(reader) == id, "READER_CHANGED");
                        var extraction = FeatureExtraction.CreateFmdFromFid(captured.Data, Constants.Formats.Fmd.ANSI);
                        Require(extraction.ResultCode == Constants.ResultCode.DP_SUCCESS && extraction.Data != null, "FMD_EXTRACTION_FAILED");
                        fmd = extraction.Data;
                        // Private pipe only; the HTTP service attests this SDK result, never caller data.
                        return new { ok = true, data = Convert.ToBase64String(fmd.Bytes), device_id = id, capture_started_at = started, captured_at = capturedAt, cleanup = true };
                    } finally {
                        if (captured != null) ClearImage(captured.Data);
                        if (fmd != null) Clear(fmd.Bytes);
                    }
                }
            } finally { if (owns) mutex.ReleaseMutex(); }
        }
    }
    static object Match(Dictionary<string, object> command) {
        byte[] probeBytes = Convert.FromBase64String((string)command["probe"]);
        Fmd probe = null;
        try {
            var imported = Importer.ImportFmd(probeBytes, Constants.Formats.Fmd.ANSI, Constants.Formats.Fmd.ANSI);
            Require(imported.ResultCode == Constants.ResultCode.DP_SUCCESS && imported.Data != null, "INVALID_FMD");
            probe = imported.Data;
            foreach (var item in (System.Collections.ArrayList)command["candidates"]) {
                var candidate = (Dictionary<string, object>)item;
                byte[] data = Convert.FromBase64String((string)candidate["data"]);
                Fmd enrolled = null;
                try {
                    var parsed = Importer.ImportFmd(data, Constants.Formats.Fmd.ANSI, Constants.Formats.Fmd.ANSI);
                    Require(parsed.ResultCode == Constants.ResultCode.DP_SUCCESS && parsed.Data != null, "INVALID_FMD");
                    enrolled = parsed.Data;
                    var result = Comparison.Compare(probe, 0, enrolled, 0);
                    Require(result.ResultCode == Constants.ResultCode.DP_SUCCESS, "MATCH_FAILED");
                    if (result.Score <= 10000) return new { ok = true, success = true, isMatch = true, match_id = Convert.ToInt32(candidate["id"]) };
                } finally { Clear(data); if (enrolled != null) Clear(enrolled.Bytes); }
            }
            return new { ok = true, success = true, isMatch = false, match_id = (int?)null };
        } finally { Clear(probeBytes); if (probe != null) Clear(probe.Bytes); }
    }
    static int Main() {
        try {
            var command = Json.Deserialize<Dictionary<string, object>>(Console.ReadLine());
            string mode = (string)command["mode"];
            object result = mode == "match" ? Match(command) : Capture(command, mode == "probe");
            Reply(result);
            return 0;
        } catch (InvalidOperationException error) { Reply(new { ok = false, code = error.Message }); return 1; }
          catch { Reply(new { ok = false, code = "SDK_UNAVAILABLE" }); return 1; }
    }
}
