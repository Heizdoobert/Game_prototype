REQUIRED = {'app': dict, 'enums': dict, 'constants': dict, 'config': list, 'classes': list,
            'levels': dict, 'strings': list, 'screens': list, 'secrets': list, 'coverage': dict}

def validate(spec):
    errs = [f'missing or wrong type: {k}' for k, t in REQUIRED.items() if not isinstance(spec.get(k), t)]
    app = spec.get('app') if isinstance(spec.get('app'), dict) else {}
    errs += [f'app.{k} must be a string' for k in ('package', 'engine', 'version') if not isinstance(app.get(k), str)]
    for s in spec.get('secrets') if isinstance(spec.get('secrets'), list) else []:
        if not isinstance(s, dict) or set(s) != {'file', 'key'}:
            errs.append('secrets entries must be exactly {file, key} (never values)')
    if errs: raise ValueError('; '.join(errs))
