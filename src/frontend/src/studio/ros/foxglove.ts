/**
 * One Foxglove WebSocket connection to the simulation's Foxglove Bridge (ROS 2 Humble).
 * Channels are advertised by the bridge with their ROS 2 message definitions; messages arrive
 * CDR-encoded and are decoded with the official Foxglove ROS 2 serializer. Views subscribe by
 * topic name; the connection subscribes to a channel only while someone listens to it.
 */
import { FoxgloveClient, type Channel } from '@foxglove/ws-protocol';
import { parse } from '@foxglove/rosmsg';
import { MessageReader } from '@foxglove/rosmsg2-serialization';
import { useEffect, useRef } from 'react';
import { create } from 'zustand';

export type RosStatus = 'idle' | 'connecting' | 'connected' | 'closed';
export interface TopicInfo {
  topic: string;
  type: string;
  count: number;
  hz: number;
}
interface RosState {
  url: string | null;
  status: RosStatus;
  error: string | null;
  topics: Record<string, TopicInfo>;
}
export const useRos = create<RosState>(() => ({ url: null, status: 'idle', error: null, topics: {} }));

type Handler = (msg: any, receivedAt: number) => void; // eslint-disable-line @typescript-eslint/no-explicit-any
type Decoded = Channel & { reader?: MessageReader | null };

class RosConnection {
  private client: FoxgloveClient | null = null;
  private channels = new Map<number, Decoded>();
  private byTopic = new Map<string, number>();
  private handlers = new Map<string, Set<Handler>>();
  private subIds = new Map<string, number>();
  private subTopic = new Map<number, string>();
  private counts = new Map<string, number>();
  private url: string | null = null;
  private retry = 0;
  private timer = 0;
  private ticker = 0;

  connect(url: string | null) {
    if (url === this.url) return;
    this.close();
    this.url = url;
    useRos.setState({ url, status: url ? 'connecting' : 'idle', error: null, topics: {} });
    if (url) this.open(url);
  }

  private open(url: string) {
    let ws: WebSocket;
    try {
      ws = new WebSocket(url, ['foxglove.sdk.v1', FoxgloveClient.SUPPORTED_SUBPROTOCOL]);
    } catch (e) {
      useRos.setState({ status: 'closed', error: (e as Error).message });
      return;
    }
    // The browser WebSocket satisfies the client's interface; only the TS lib types differ on SharedArrayBuffer.
    const client = new FoxgloveClient({ ws: ws as unknown as ConstructorParameters<typeof FoxgloveClient>[0]['ws'] });
    this.client = client;
    client.on('open', () => {
      this.retry = 0;
      useRos.setState({ status: 'connected', error: null });
    });
    client.on('error', (e) => useRos.setState({ error: e instanceof Error ? e.message : String(e) }));
    client.on('close', () => {
      if (this.client !== client) return;
      this.reset();
      useRos.setState({ status: 'closed', topics: {} });
      window.clearTimeout(this.timer);
      this.timer = window.setTimeout(() => this.url === url && this.open(url), Math.min(5000, 400 * 2 ** this.retry++));
    });
    client.on('advertise', (channels) => {
      for (const ch of channels) {
        this.channels.set(ch.id, ch);
        this.byTopic.set(ch.topic, ch.id);
        if (this.handlers.get(ch.topic)?.size) this.subscribeChannel(ch.topic);
      }
      this.publishTopics();
    });
    client.on('unadvertise', (ids) => {
      for (const id of ids) {
        const ch = this.channels.get(id);
        if (!ch) continue;
        this.channels.delete(id);
        if (this.byTopic.get(ch.topic) === id) this.byTopic.delete(ch.topic);
        const sid = this.subIds.get(ch.topic);
        if (sid != null) {
          this.subIds.delete(ch.topic);
          this.subTopic.delete(sid);
        }
      }
      this.publishTopics();
    });
    client.on('message', ({ subscriptionId, data }) => {
      const topic = this.subTopic.get(subscriptionId);
      if (!topic) return;
      const ch = this.channels.get(this.byTopic.get(topic) ?? -1);
      if (!ch) return;
      const msg = this.decode(ch, data);
      if (msg == null) return;
      this.counts.set(topic, (this.counts.get(topic) ?? 0) + 1);
      const now = performance.now() / 1000;
      for (const h of this.handlers.get(topic) ?? []) {
        try {
          h(msg, now);
        } catch (e) {
          console.error(`处理话题 ${topic} 出错`, e);
        }
      }
    });
    window.clearInterval(this.ticker);
    this.ticker = window.setInterval(() => this.publishTopics(true), 1000);
  }

  private decode(ch: Decoded, data: ArrayBufferView) {
    if (ch.reader === undefined) {
      try {
        const schemaEncoding = (ch as Channel & { schemaEncoding?: string }).schemaEncoding ?? 'ros2msg';
        ch.reader = ch.encoding === 'cdr' && schemaEncoding === 'ros2msg' ? new MessageReader(parse(ch.schema, { ros2: true })) : null;
      } catch (e) {
        console.warn(`无法解析 ${ch.topic} 的消息定义`, e);
        ch.reader = null;
      }
    }
    return ch.reader ? ch.reader.readMessage(new Uint8Array(data.buffer, data.byteOffset, data.byteLength)) : null;
  }

  private subscribeChannel(topic: string) {
    const id = this.byTopic.get(topic);
    if (id == null || this.subIds.has(topic) || !this.client) return;
    const sid = this.client.subscribe(id);
    this.subIds.set(topic, sid);
    this.subTopic.set(sid, topic);
  }

  subscribe(topic: string, handler: Handler): () => void {
    let set = this.handlers.get(topic);
    if (!set) this.handlers.set(topic, (set = new Set()));
    set.add(handler);
    this.subscribeChannel(topic);
    return () => {
      set!.delete(handler);
      if (set!.size) return;
      const sid = this.subIds.get(topic);
      if (sid != null && this.client) {
        try {
          this.client.unsubscribe(sid);
        } catch {
          /* connection already gone */
        }
        this.subIds.delete(topic);
        this.subTopic.delete(sid);
      }
    };
  }

  /** Topics currently advertised, with their message types. */
  channelsOfType(type: string): string[] {
    return [...this.channels.values()].filter((c) => c.schemaName === type).map((c) => c.topic);
  }

  private publishTopics(rates = false) {
    const topics: Record<string, TopicInfo> = {};
    const prev = useRos.getState().topics;
    for (const ch of this.channels.values()) {
      const count = this.counts.get(ch.topic) ?? 0;
      const before = prev[ch.topic]?.count ?? 0;
      topics[ch.topic] = { topic: ch.topic, type: ch.schemaName, count, hz: rates ? count - before : prev[ch.topic]?.hz ?? 0 };
    }
    useRos.setState({ topics });
  }

  private reset() {
    this.channels.clear();
    this.byTopic.clear();
    this.subIds.clear();
    this.subTopic.clear();
  }

  close() {
    window.clearTimeout(this.timer);
    window.clearInterval(this.ticker);
    const client = this.client;
    this.client = null;
    this.reset();
    try {
      client?.close();
    } catch {
      /* already closed */
    }
  }
}

export const ros = new RosConnection();

/** Calls `handler` for every message on `topic` while the component is mounted. */
export function useRosTopic(topic: string | null, handler: Handler) {
  const ref = useRef(handler);
  ref.current = handler;
  useEffect(() => (topic ? ros.subscribe(topic, (m, t) => ref.current(m, t)) : undefined), [topic]);
}
