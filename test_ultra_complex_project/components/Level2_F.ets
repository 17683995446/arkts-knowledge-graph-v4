/**
 * Level2_F.ets - 二级组件F
 */

import { Service_008 } from '../services/Service_008';
import { Level3_F } from './Level3_F';

@Component
struct Level2_F {
  @State private sliderValue: number = 50;
  
  private service008: Service_008 = new Service_008();
  
  private onSliderChange = (value: number): void => {
    this.slider1(value);
  }
  
  private slider1(v: number): void { this.slider2(v); }
  private slider2(v: number): void { this.slider3(v); }
  private slider3(v: number): void { this.slider4(v); }
  private slider4(v: number): void { this.slider5(v); }
  private slider5(v: number): void { this.slider6(v); }
  private slider6(v: number): void { this.slider7(v); }
  private slider7(v: number): void { this.slider8(v); }
  private slider8(v: number): void { this.slider9(v); }
  private slider9(v: number): void { this.slider10(v); }
  
  private slider10(v: number): void {
    this.sliderValue = v;
    this.service008.method008();
  }
  
  build() {
    Column() {
      Level3_F()
      Slider({ value: this.sliderValue, min: 0, max: 100 })
        .onChange(this.onSliderChange)
    }
  }
}
