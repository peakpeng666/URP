"""Cross-file binding of the exact four-slot pilot; no subprocess/model calls."""
import hashlib,json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parent
class ProtocolBindingTests(unittest.TestCase):
 def test_four_slots_and_schema_are_bound(self):
  read=lambda name:json.loads((ROOT/name).read_text())
  protocol=read('protocol.json');pilot=read('preregistered_pilot.json');prepared=read('transport_preparation.json');transport=read('transport_protocol.json')
  select=lambda xs:[{'id':x['id'],'seed':x['seed']} for x in xs]
  slots=select(prepared['slots'])
  self.assertEqual(slots,[{'id':name,'seed':2026100800+i} for i,name in enumerate(['fixed_transcription','design_0','design_1','design_2'])])
  self.assertEqual(select(protocol['requests']),slots);self.assertEqual(pilot['slots'],slots);self.assertEqual(transport['slots'],slots)
  self.assertEqual(protocol['model_requests_max'],4);self.assertEqual(protocol['score_requests_max'],12);self.assertEqual(pilot['requests'],4)
  h=hashlib.sha256((ROOT/'generation_schema.json').read_bytes()).hexdigest();schema=read('generation_schema.json')
  for d in [protocol['decoding'],pilot,prepared,transport]:
   self.assertEqual(d['schema_file'],'generation_schema.json');self.assertEqual(d['schema_sha256'],h)
  prompts=read('prompts.json')
  for i,s in enumerate(prepared['slots']):
   req=read(s['request_file']);self.assertEqual(req['seed'],slots[i]['seed']);self.assertEqual(req['json_schema'],schema)
   self.assertEqual(hashlib.sha256((ROOT/s['request_file']).read_bytes()).hexdigest(),s['request_sha256'])
   self.assertEqual((ROOT/protocol['requests'][i]['prompt']).read_text(),prompts[i]['prompt'])
   self.assertEqual(protocol['requests'][i]['request_file'],s['request_file'])
if __name__=='__main__':unittest.main(verbosity=2)
