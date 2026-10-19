"""Verify the exact project-local TF2 candidate and system ABI before using it.

The manifests in this directory are the laptop audit. When those system files are
present and match, only the audited library hash is accepted. A machine profile
under runtime/profiles/ is used only when the laptop libraries are not the ones
installed here, and only if the audited source hash still matches.
"""
import hashlib
import json
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
PROFILES = BASE / 'runtime/profiles'


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ok(files):
    for name, expected in files.items():
        path = Path(name)
        if not path.is_file() or _sha(path) != expected:
            return False
    return True


def _refuse(name):
    raise RuntimeError('TF2/GUI overlay fingerprint changed or file missing: ' + name +
                       '. Rebuild and revalidate explicitly; do not bypass this check.')


def _image_profile(name):
    if os.environ.get('URP_SIM_PROFILE') != 'image':
        return None
    path = PROFILES / name
    if not path.is_file():
        return None
    profile = json.loads(path.read_text())
    return profile if profile.get('scope') == 'image' else None


def verified_candidate():
    manifest = json.loads((BASE / 'tf2-overlay-manifest.json').read_text())
    candidate = BASE / manifest['candidate_library']
    source = BASE / 'tf-repro/buffer_candidate.cpp'
    laptop = {**manifest['system_libraries'],
              str(candidate): manifest['candidate_sha256'],
              str(source): manifest['source_sha256']}
    if _ok(laptop):
        return candidate
    image = _image_profile('tf.json')
    if image is not None and image.get('source_sha256') == manifest['source_sha256']:
        built = BASE / image.get('candidate_library', manifest['candidate_library'])
        if _ok({**image.get('system_libraries', {}), str(built): image.get('candidate_sha256')}):
            return built
    if not source.is_file() or _sha(source) != manifest['source_sha256']:
        _refuse(str(source))
    profile_path = PROFILES / 'tf.json'
    if profile_path.is_file():
        profile = json.loads(profile_path.read_text())
        built = BASE / profile.get('candidate_library', manifest['candidate_library'])
        if (profile.get('source_sha256') == manifest['source_sha256']
                and _ok({**profile.get('system_libraries', {}), str(built): profile.get('candidate_sha256')})):
            return built
    _refuse('system libraries differ from the laptop TF audit and no matching machine profile is recorded')


def verified_gui_lifetime():
    manifest = json.loads((BASE / 'gui-overlay-manifest.json').read_text())
    library = BASE / manifest['library']
    if _ok(manifest['files']):
        return library
    expected_source = next((digest for name, digest in manifest['files'].items() if name.endswith('gui-plugin-lifetime.cpp')), None)
    image = _image_profile('gui.json')
    if image is not None and image.get('source_sha256') == expected_source:
        built = BASE / image.get('library', manifest['library'])
        if _ok({**image.get('system_libraries', {}), str(built): image.get('library_sha256')}):
            return built
    source = BASE / 'gui-plugin-lifetime.cpp'
    expected = expected_source
    if expected is None or not source.is_file() or _sha(source) != expected:
        _refuse(str(source))
    profile_path = PROFILES / 'gui.json'
    if profile_path.is_file():
        profile = json.loads(profile_path.read_text())
        built = BASE / profile.get('library', manifest['library'])
        if (profile.get('source_sha256') == expected
                and _ok({**profile.get('system_libraries', {}), str(built): profile.get('library_sha256')})):
            return built
    _refuse('system libraries differ from the laptop GUI audit and no matching machine profile is recorded')


if __name__ == '__main__':
    print(verified_candidate())
