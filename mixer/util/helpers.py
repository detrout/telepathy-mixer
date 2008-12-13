def prefix(pre, *vdict, **dictionary):
    if dictionary or (vdict and isinstance(vdict[0], dict)):
        for d in vdict:
            dictionary.update(d)
        return dict([(pre + key, value) for key, value in dictionary.items()])
    else:
        return [pre + val for val in vdict]