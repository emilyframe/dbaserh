from dbaserh import DBASERH

detector = DBASERH(serial=16291937, hvt=1100,
                    fgn=0.5, pw=0.75, realtime=30,
                    sleept=0.05, energy=[15, 42, 75, 130, 146, 279],
                    channel=[59.5, 356, 662, 1173, 1332, 2614])

hf = detector.measure_list_mode(disp=True)

detector.end_process()
