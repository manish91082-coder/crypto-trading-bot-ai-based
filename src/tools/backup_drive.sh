#!/usr/bin/env bash
# Full project backup to Google Drive.
#   packed/  : heavy folders (archive, data, logs, .git, .claude) streamed as one .tar each,
#              plus _project_light_files.tar with everything else (code, reports, configs, .env).
#   mirror/  : the same light files again, file by file, so they can be opened on Drive (runs last).
# Drive needs about 1 s per file, so tens of thousands of small data files would take days one by one.
# Each tar is hashed (MD5) while it streams, and the hash is compared with the one Drive reports.
# A pack whose files (path, size, mtime) did not change since its last verified upload is skipped.
# Restore one pack: tar -xf <name>.tar -C "<project folder>"
set -u
ROOT="/e/crypto trading bot ai based 9 oct 2026"
DEST="gdrive:CRYPTO_TRADING_BOT_LAPTOP_FULL_BACKUP"
LOGD="$ROOT/logs/backup_drive"
MAN="$LOGD/packs_manifest.tsv"          # name, source, bytes, md5_local, md5_drive, status, tar_exit, fingerprint, utc
SPLIT_MB=4096                           # a folder bigger than this is packed one level deeper
JOBS=3
mkdir -p "$LOGD/tmp"
[ -s "$MAN" ] || printf 'name\tsource\tbytes\tmd5_local\tmd5_drive\tstatus\ttar_exit\tfingerprint\tutc\n' > "$MAN"
cd "$ROOT" || exit 1

HEAVY='archive data logs .git .claude'
fingerprint() {  # $1 = rel dir, $2 = "loose" for files directly in it only, "light" for everything outside $HEAVY
  case "${2:-}" in
    loose) find "$1" -maxdepth 1 -type f -printf '%P\t%s\t%T@\n' ;;
    light) find . \( -path ./archive -o -path ./data -o -path ./logs -o -path ./.git -o -path ./.claude -o -name __pycache__ \) -prune -o -type f -printf '%P\t%s\t%T@\n' ;;
    *) find "$1" -type f -printf '%P\t%s\t%T@\n' ;;
  esac | sort | md5sum | cut -c1-32
}

pack() {  # $1 = rel dir, $2 = "loose" or ""
  local rel="$1" mode="${2:-}" name fp t; name="$(echo "$rel" | sed 's#/#__#g; s# #_#g')"
  [ "$mode" = loose ] && name="${name}__loose_files"
  [ "$mode" = light ] && name="_project_light_files"
  fp=$(fingerprint "$rel" "$mode")
  if awk -F'\t' -v n="$name.tar" -v f="$fp" '$1==n && $8==f && $6 ~ /^OK/ {x=1} END{exit !x}' "$MAN"; then
    echo "$(date -u +%FT%TZ) SKIP unchanged $name.tar"; return 0; fi
  t="$LOGD/tmp/$name"; rm -f "$t".md5 "$t".size
  if [ "$mode" = loose ]; then
    find "$rel" -maxdepth 1 -type f -print0 | tar -cf - --null -T - 2>"$t.err"
  elif [ "$mode" = light ]; then
    tar -cf - --exclude=./archive --exclude=./data --exclude=./logs --exclude=./.git --exclude=./.claude --exclude='__pycache__' . 2>"$t.err"
  else
    tar -cf - --exclude='__pycache__' "$rel" 2>"$t.err"
  fi | tee >(md5sum | cut -c1-32 > "$t.md5") >(wc -c > "$t.size") \
     | rclone rcat "$DEST/packed/$name.tar" --drive-chunk-size 64M --retries 5 --low-level-retries 20 2>"$t.rclone.err"
  local st=("${PIPESTATUS[@]}")
  for _ in $(seq 60); do [ -s "$t.md5" ] && [ -s "$t.size" ] && break; sleep 1; done
  local ml md bytes status
  ml=$(cat "$t.md5" 2>/dev/null); bytes=$(tr -d ' ' < "$t.size" 2>/dev/null)
  md=$(rclone md5sum "$DEST/packed/$name.tar" 2>/dev/null | cut -c1-32)
  if [ "${st[-1]}" != 0 ]; then status=FAIL_UPLOAD
  elif [ -z "$ml" ] || [ "$ml" != "$md" ]; then status=FAIL_MD5
  elif [ "${st[0]}" = 0 ]; then status=OK
  else status=OK_FILES_CHANGED_DURING_READ; fi    # tar exit 1: a live log grew while it was read
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name.tar" "$rel" "$bytes" "$ml" "$md" "$status" "${st[0]}" "$fp" "$(date -u +%FT%TZ)" >> "$MAN"
  echo "$(date -u +%FT%TZ) $status $name.tar $bytes bytes"
}

units() {  # one line per pack: "<mode>\t<rel>"
  printf 'light\t.\n\t.git\n\t.claude\n'
  for top in logs data archive; do
    [ -n "$(find "$top" -maxdepth 1 -type f -print -quit)" ] && printf 'loose\t%s\n' "$top"
    find "$top" -mindepth 1 -maxdepth 1 -type d | sort | while read -r d; do
      [ "$d" = logs/backup_drive ] && continue
      if [ "$(du -s --block-size=1M "$d" | cut -f1)" -gt "$SPLIT_MB" ]; then
        [ -n "$(find "$d" -maxdepth 1 -type f -print -quit)" ] && printf 'loose\t%s\n' "$d"
        find "$d" -mindepth 1 -maxdepth 1 -type d | sort | sed 's/^/\t/'
      else printf '\t%s\n' "$d"; fi
    done
  done
}

[ "${1:-}" = --pack ] && { pack "$2" "${3:-}"; exit; }   # one pack only (testing)

echo "$(date -u +%FT%TZ) START"
export -f pack fingerprint; export ROOT DEST LOGD MAN
units > "$LOGD/units.tsv"
echo "$(date -u +%FT%TZ) UNITS $(wc -l < "$LOGD/units.tsv")"
tr '\t' '\001' < "$LOGD/units.tsv" | xargs -d '\n' -P "$JOBS" -I{} bash -c 'IFS=$'"'"'\001'"'"' read -r m r <<< "$1"; pack "$r" "$m"' _ {}
echo "$(date -u +%FT%TZ) PACKS finished"

# browsable copy of the light files, last: Drive throttles per-file requests, and the packs already hold these files
rclone copy "$ROOT" "$DEST/mirror" --exclude '/archive/**' --exclude '/data/**' --exclude '/logs/**' \
  --exclude '/.git/**' --exclude '/.claude/**' --exclude '__pycache__/**' --exclude '.pytest_cache/**' \
  --transfers 4 --tpslimit 4 --log-file "$LOGD/mirror.log" --log-level NOTICE
echo "$(date -u +%FT%TZ) MIRROR exit $?"

# the backup's own logs last, file by file
rclone copy "$LOGD" "$DEST/mirror/logs/backup_drive" --exclude 'tmp/**' --log-level NOTICE
echo "$(date -u +%FT%TZ) DONE ok=$(awk -F'\t' 'NR>1 && $6 ~ /^OK/' "$MAN" | cut -f1 | sort -u | wc -l) fail=$(awk -F'\t' 'NR>1 && $6 ~ /^FAIL/' "$MAN" | wc -l)"
