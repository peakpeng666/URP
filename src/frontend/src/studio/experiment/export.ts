import { LabApiError } from '../../lab/api';
import { studio, type CallOptions, type ExperimentRecordEnvelope } from '../api';

export interface RecordDownloadResult {
  envelope: ExperimentRecordEnvelope;
  fileName: string;
  serialized: string;
}

export async function downloadServerRecord(
  runId: string,
  options: CallOptions & { onDownload?: (blob: Blob, fileName: string) => void } = {},
): Promise<RecordDownloadResult> {
  // Keep the server bytes: parsing + JSON.stringify changes 1.0 to 1, large integers,
  // and exponent spelling, which can invalidate the server's canonical record digest.
  const serialized = await studio.runRecordText(runId, { signal: options.signal, timeoutMs: options.timeoutMs });
  const envelope = JSON.parse(serialized) as ExperimentRecordEnvelope;
  if (
    envelope?.record?.schema !== 'agri-workbench.experiment-record/2'
    || envelope.record.run_id !== runId
    || typeof envelope.integrity?.sha256 !== 'string'
    || !envelope.integrity.sha256
    || typeof envelope.assembled_utc !== 'string'
    || !envelope.assembled_utc
  ) {
    throw new LabApiError('服务端 record envelope 的 schema、run_id、integrity 或 assembled_utc 不完整；未触发下载', 'bad_response', 200);
  }
  const fileName = `experiment-${runId}.json`;
  const blob = new Blob([serialized], { type: 'application/json' });
  if (options.onDownload) {
    options.onDownload(blob, fileName);
  } else {
    const href = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = href;
    link.download = fileName;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(href), 2000);
  }
  return { envelope, fileName, serialized };
}
