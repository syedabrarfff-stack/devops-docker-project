// AudioWorkletProcessor: captures the mic's native-rate Float32 samples,
// linearly resamples down to 16kHz (Deepgram's expected rate for the demo
// widget — see backend/app/services/demo_call_manager.py), converts to
// Int16 PCM, and posts each ~20ms frame back to the main thread as a
// transferable ArrayBuffer.
//
// A simple linear-interpolation resampler is intentionally used here rather
// than a proper windowed-sinc resampler: this feeds speech recognition, not
// music playback, and the quality difference is inaudible for that purpose
// while being trivial to implement without external libraries in a Worklet
// (which has no access to the DOM, fetch, or npm-installed code).
class PCMDownsampler extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.targetRate = (options.processorOptions && options.processorOptions.targetRate) || 16000;
    this.sourceRate = sampleRate; // AudioWorkletGlobalScope's native context rate
    this.ratio = this.sourceRate / this.targetRate;
    this.carry = 0; // fractional position left over between render quanta
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0] || input[0].length === 0) return true;
    const channel = input[0];

    const outLength = Math.floor((channel.length - this.carry) / this.ratio);
    if (outLength <= 0) {
      this.carry -= channel.length;
      return true;
    }

    const out = new Int16Array(outLength);
    let srcPos = this.carry;
    for (let i = 0; i < outLength; i++) {
      const idx = Math.floor(srcPos);
      const frac = srcPos - idx;
      const s0 = channel[idx] || 0;
      const s1 = channel[idx + 1] !== undefined ? channel[idx + 1] : s0;
      const sample = s0 + (s1 - s0) * frac;
      const clamped = Math.max(-1, Math.min(1, sample));
      out[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
      srcPos += this.ratio;
    }
    this.carry = srcPos - channel.length;

    this.port.postMessage(out.buffer, [out.buffer]);
    return true;
  }
}

registerProcessor("pcm-downsampler", PCMDownsampler);
