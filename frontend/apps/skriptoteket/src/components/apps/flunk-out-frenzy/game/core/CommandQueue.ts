/**
 * Lightweight runtime command queue for Flunk-Out Frenzy.
 *
 * The runtime loop owns command draining so Vue and DOM input adapters can
 * enqueue intent without mutating runtime state directly. The queue stays
 * generic so later physics and rules slices can reuse it without coupling to
 * any specific command family.
 */

export class CommandQueue<TCommand> {
  private readonly commands: TCommand[] = [];

  push(command: TCommand): void {
    this.commands.push(command);
  }

  drain(): TCommand[] {
    return this.commands.splice(0, this.commands.length);
  }

  clear(): void {
    this.commands.length = 0;
  }
}
