#!/usr/bin/env bash
# Install the idle-safe cleanup wrapper and its two existing hourly unit pairs.

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
libexec_dir="/usr/local/libexec"
systemctl_command=(systemctl)

sources=(
  "$repo_root/scripts/hemma_cleanup_if_running.sh"
  "$repo_root/systemd/skriptoteket-session-files-cleanup.service"
  "$repo_root/systemd/skriptoteket-session-files-cleanup.timer"
  "$repo_root/systemd/skriptoteket-sandbox-snapshots-cleanup.service"
  "$repo_root/systemd/skriptoteket-sandbox-snapshots-cleanup.timer"
)
destinations=(
  "$libexec_dir/skriptoteket-cleanup-if-running"
  /etc/systemd/system/skriptoteket-session-files-cleanup.service
  /etc/systemd/system/skriptoteket-session-files-cleanup.timer
  /etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.service
  /etc/systemd/system/skriptoteket-sandbox-snapshots-cleanup.timer
)
modes=(0755 0644 0644 0644 0644)
timers=(
  skriptoteket-session-files-cleanup.timer
  skriptoteket-sandbox-snapshots-cleanup.timer
)
transaction_dir=""
destination_existed=()
timer_enabled_states=()
timer_active_states=()
libexec_created=0
current_enabled_state=""
current_active_state=""

reset_transaction_state() {
  transaction_dir=""
  destination_existed=()
  timer_enabled_states=()
  timer_active_states=()
  libexec_created=0
  current_enabled_state=""
  current_active_state=""
}

cleanup_transaction() {
  if [[ -n "$transaction_dir" && -d "$transaction_dir" ]]; then
    rm -rf -- "$transaction_dir"
  fi
}

read_timer_state() {
  local timer="$1"
  local enabled_status
  local active_status

  if current_enabled_state="$("${systemctl_command[@]}" is-enabled "$timer" 2>&1)"; then
    enabled_status=0
  else
    enabled_status=$?
  fi
  if current_active_state="$("${systemctl_command[@]}" is-active "$timer" 2>&1)"; then
    active_status=0
  else
    active_status=$?
  fi

  case "$current_enabled_state:$enabled_status" in
    enabled:0|disabled:1) ;;
    *)
      echo "Refusing cleanup-unit installation: $timer has unsupported enabled state: $current_enabled_state" >&2
      return 1
      ;;
  esac
  case "$current_active_state:$active_status" in
    active:0|inactive:3) ;;
    *)
      echo "Refusing cleanup-unit installation: $timer has unsupported active state: $current_active_state" >&2
      return 1
      ;;
  esac
}

restore_timer_states() {
  local index
  local timer
  local restore_failed=0

  for index in "${!timers[@]}"; do
    timer="${timers[$index]}"
    if [[ "${timer_enabled_states[$index]}" == "enabled" ]]; then
      if ! "${systemctl_command[@]}" enable "$timer"; then
        echo "Rollback failed to enable $timer." >&2
        restore_failed=1
      fi
    else
      if ! "${systemctl_command[@]}" disable "$timer"; then
        echo "Rollback failed to disable $timer." >&2
        restore_failed=1
      fi
    fi
    if [[ "${timer_active_states[$index]}" == "active" ]]; then
      if ! "${systemctl_command[@]}" start "$timer"; then
        echo "Rollback failed to start $timer." >&2
        restore_failed=1
      fi
    else
      if ! "${systemctl_command[@]}" stop "$timer"; then
        echo "Rollback failed to stop $timer." >&2
        restore_failed=1
      fi
    fi
  done

  return "$restore_failed"
}

rollback() {
  local index
  local rollback_failed=0

  for index in "${!destinations[@]}"; do
    if [[ "${destination_existed[$index]}" == "yes" ]]; then
      if ! cp -p -- "$transaction_dir/$index" "${destinations[$index]}"; then
        echo "Rollback failed to restore ${destinations[$index]}." >&2
        rollback_failed=1
      fi
    elif ! rm -f -- "${destinations[$index]}"; then
      echo "Rollback failed to remove ${destinations[$index]}." >&2
      rollback_failed=1
    fi
  done

  if ! "${systemctl_command[@]}" daemon-reload; then
    echo "Rollback failed to reload systemd." >&2
    rollback_failed=1
  fi
  if ! restore_timer_states; then
    echo "Rollback failed to restore cleanup timer states." >&2
    rollback_failed=1
  fi
  if [[ "$libexec_created" -eq 1 ]] && [[ -d "$libexec_dir" ]] && [[ -z "$(find "$libexec_dir" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    if ! rmdir "$libexec_dir"; then
      echo "Rollback failed to remove empty /usr/local/libexec." >&2
      rollback_failed=1
    fi
  fi

  return "$rollback_failed"
}

on_error() {
  local original_status="$1"
  local rollback_status=0

  trap - ERR HUP INT TERM
  echo "Cleanup-unit installation failed; rolling back authorized destinations." >&2
  rollback || rollback_status=$?
  cleanup_transaction || rollback_status=$?
  if [[ "$rollback_status" -ne 0 ]]; then
    echo "Cleanup-unit rollback did not complete successfully." >&2
  fi
  exit "$original_status"
}

main() {
  local index
  local source
  local destination
  local timer

  set -euo pipefail
  set -E
  reset_transaction_state

  if [[ "$(id -u)" -ne 0 ]]; then
    echo "Refusing to install cleanup units: run with sudo." >&2
    return 1
  fi
  for source in "${sources[@]}"; do
    if [[ ! -f "$source" ]]; then
      echo "Required cleanup source is missing: $source" >&2
      return 1
    fi
  done
  for destination in "${destinations[@]}"; do
    if [[ -L "$destination" || ( -e "$destination" && ! -f "$destination" ) ]]; then
      echo "Refusing cleanup-unit installation: destination is not a regular file: $destination" >&2
      return 1
    fi
  done
  if [[ -L "$libexec_dir" ]]; then
    echo "Refusing cleanup-unit installation: /usr/local/libexec is a symbolic link." >&2
    return 1
  fi

  umask 077
  transaction_dir="$(mktemp -d "${TMPDIR:-/tmp}/skriptoteket-cleanup-units.XXXXXX")"
  if ! chmod 0700 "$transaction_dir"; then
    cleanup_transaction
    return 1
  fi
  for index in "${!destinations[@]}"; do
    if [[ -e "${destinations[$index]}" ]]; then
      if ! cp -p -- "${destinations[$index]}" "$transaction_dir/$index"; then
        cleanup_transaction
        return 1
      fi
      destination_existed+=(yes)
    else
      destination_existed+=(no)
    fi
  done
  for timer in "${timers[@]}"; do
    if ! read_timer_state "$timer"; then
      cleanup_transaction
      return 1
    fi
    timer_enabled_states+=("$current_enabled_state")
    timer_active_states+=("$current_active_state")
  done

  trap 'on_error $?' ERR
  trap 'on_error 1' HUP TERM
  trap 'on_error 130' INT

  if [[ ! -d "$libexec_dir" ]]; then
    mkdir "$libexec_dir"
    libexec_created=1
  fi
  for index in "${!destinations[@]}"; do
    install -m "${modes[$index]}" "${sources[$index]}" "${destinations[$index]}"
  done

  "${systemctl_command[@]}" daemon-reload
  for index in "${!timers[@]}"; do
    read_timer_state "${timers[$index]}"
    if [[ "$current_enabled_state" != "${timer_enabled_states[$index]}" || "$current_active_state" != "${timer_active_states[$index]}" ]]; then
      echo "Cleanup timer state changed unexpectedly: ${timers[$index]}." >&2
      return 1
    fi
  done

  trap - ERR HUP INT TERM
  cleanup_transaction

  printf 'Installed cleanup destinations: %s; %s; %s; %s; %s\n' "${destinations[@]}"
  printf 'Preserved timer states: %s=%s/%s; %s=%s/%s\n' \
    "${timers[0]}" "${timer_enabled_states[0]}" "${timer_active_states[0]}" \
    "${timers[1]}" "${timer_enabled_states[1]}" "${timer_active_states[1]}"
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  main
fi
