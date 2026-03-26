import sys
import os

def parse_cfg(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return None

    config = {}
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('%'):
                continue
            
            parts = line.split()
            cmd = parts[0]
            args = parts[1:]

            if cmd == 'profileCfg':
                config['profile'] = {
                    'profileId': int(args[0]),
                    'startFreq_GHz': float(args[1]),
                    'idleTime_us': float(args[2]),
                    'adcStartTime_us': float(args[3]),
                    'rampEndTime_us': float(args[4]),
                    'txOutPower': int(args[5]),
                    'txPhaseShift': int(args[6]),
                    'freqSlope_MHz_us': float(args[7]),
                    'txStartTime_us': float(args[8]),
                    'numAdcSamples': int(args[9]),
                    'sampleRate_ksps': int(args[10]),
                    'hpfCornerFreq1': int(args[11]),
                    'hpfCornerFreq2': int(args[12]),
                    'rxGain_dB': int(args[13])
                }
            elif cmd == 'frameCfg':
                config['frame'] = {
                    'chirpStartIdx': int(args[0]),
                    'chirpEndIdx': int(args[1]),
                    'numLoops': int(args[2]),
                    'numFrames': int(args[3]),
                    'framePeriodicity_ms': float(args[4]),
                    'triggerSelect': int(args[5]),
                    'frameTriggerDelay_ms': float(args[6])
                }
            elif cmd == 'channelCfg':
                config['channel'] = {
                    'rxAntBitmap': int(args[0]),
                    'txAntBitmap': int(args[1]),
                    'cascading': int(args[2])
                }

    return config

def print_parameters(config):
    if not config:
        return

    print("="*40)
    print("      TI RADAR SIGNAL PARAMETERS")
    print("="*40)

    if 'profile' in config:
        p = config['profile']
        print("\n[ Profile Configuration ]")
        print(f"  Start Frequency:      {p['startFreq_GHz']} GHz")
        print(f"  Slope:               {p['freqSlope_MHz_us']} MHz/us")
        print(f"  ADC Samples:          {p['numAdcSamples']}")
        print(f"  Sample Rate:          {p['sampleRate_ksps']} ksps")
        print(f"  Idle Time:            {p['idleTime_us']} us")
        print(f"  Ramp End Time:        {p['rampEndTime_us']} us")
        print(f"  RX Gain:              {p['rxGain_dB']} dB")
        
        # Derived parameters
        bandwidth = p['freqSlope_MHz_us'] * (p['numAdcSamples'] / p['sampleRate_ksps'] * 1000)
        print(f"  Calculated Bandwidth: {bandwidth:.2f} MHz")

    if 'frame' in config:
        f = config['frame']
        print("\n[ Frame Configuration ]")
        print(f"  Num Loops:            {f['numLoops']}")
        print(f"  Num Frames:           {f['numFrames']}")
        print(f"  Frame Periodicity:    {f['framePeriodicity_ms']} ms")

    if 'channel' in config:
        c = config['channel']
        num_rx = bin(c['rxAntBitmap']).count('1')
        num_tx = bin(c['txAntBitmap']).count('1')
        print("\n[ Channel Configuration ]")
        print(f"  RX Antennas:          {num_rx} (Bitmap: {c['rxAntBitmap']})")
        print(f"  TX Antennas:          {num_tx} (Bitmap: {c['txAntBitmap']})")

    print("="*40)

if __name__ == "__main__":
    file_name = "Test3.cfg"
    if len(sys.argv) > 1:
        file_name = sys.argv[1]
    
    cfg_data = parse_cfg(file_name)
    if cfg_data:
        print_parameters(cfg_data)
