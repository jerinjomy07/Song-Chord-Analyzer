import re
from urllib.parse import quote
from starlette.responses import PlainTextResponse, JSONResponse

title = "@SaiAbhyankkar - Radhimaa (Music Video) \uff5c Bhagyashri Borse \uff5c Thejo Bharathwaj \uff5c Think Indie"

def get_safe_export_filename(title: str, extension: str):
    safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f\uff5c]', '_', title).strip()
    safe_title = re.sub(r'_+', '_', safe_title).strip(' ._')
    if not safe_title:
        safe_title = "Song"
    ascii_title = safe_title.encode('ascii', 'ignore').decode('ascii').strip(' ._')
    if not ascii_title:
        ascii_title = "Song"
    filename_ascii = f"{ascii_title}_Chords.{extension}"
    filename_utf8 = f"{safe_title}_Chords.{extension}"
    disposition = f'attachment; filename="{filename_ascii}"; filename*=UTF-8\'\'{quote(filename_utf8)}'
    return filename_ascii, disposition

fn, cd = get_safe_export_filename(title, 'txt')
resp_txt = PlainTextResponse("Line 1\nLine 2", media_type="text/plain; charset=utf-8", headers={"Content-Disposition": cd})
resp_json = JSONResponse({"title": title}, headers={"Content-Disposition": cd})

print("Ascii Filename:", fn)
print("Content-Disposition:", cd)
print("TXT Response headers:", resp_txt.headers)
print("JSON Response headers:", resp_json.headers)
print("SUCCESS!")
