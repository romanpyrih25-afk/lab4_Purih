import re
import sys

CHUNK_SIZE = 64 * 1024

LOG_PATTERN = re.compile(
    rb'^\S+ \S+ \S+ \[[^\]]*\] "(?P<request>[^"]*)" '
    rb'(?P<status>\d{3}) (?P<sent>\d+|-)'
)


def read_chunks(file_obj, chunk_size=CHUNK_SIZE):
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        yield chunk


def lines_from_chunks(chunks):
    tail = b""
    for chunk in chunks:
        tail += chunk
        *lines, tail = tail.split(b"\n")
        yield from lines
    if tail:
        yield tail


def parse_line(line):
    match = LOG_PATTERN.match(line.strip())
    if not match:
        return None
    sent = match.group("sent")
    sent_bytes = 0 if sent == b"-" else int(sent)
    received_bytes = len(match.group("request"))
    return sent_bytes, received_bytes


def count_traffic(path, chunk_size=CHUNK_SIZE):
    total_sent = 0
    total_received = 0
    with open(path, "rb") as f:
        parsed = (parse_line(line) for line in lines_from_chunks(read_chunks(f, chunk_size)))
        for sent, received in (item for item in parsed if item is not None):
            total_sent += sent
            total_received += received
    return total_sent, total_received


def human(size):
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} ТБ"


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "2017_05_07_nginx.txt"
    sent, received = count_traffic(path)
    print(f"Файл: {path}")
    print(f"Надіслано байтів: {sent} ({human(sent)})")
    print(f"Прийнято байтів:  {received} ({human(received)})")
    print(f"Разом:            {sent + received} ({human(sent + received)})")


if __name__ == "__main__":
    main()
