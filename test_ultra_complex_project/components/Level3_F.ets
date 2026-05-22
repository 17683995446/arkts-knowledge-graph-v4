/**
 * Level3_F.ets - 三级组件F
 */

import { Service_019 } from '../services/Service_019';

@Component
struct Level3_F {
  @State private sliderVal: number = 50;
  
  private service019: Service_019 = new Service_019();
  
  private onSlide = (v: number): void => {
    this.slide1(v);
  }
  
  private slide1(v: number): void { this.slide2(v); }
  private slide2(v: number): void { this.slide3(v); }
  private slide3(v: number): void { this.slide4(v); }
  private slide4(v: number): void { this.slide5(v); }
  private slide5(v: number): void { this.slide6(v); }
  private slide6(v: number): void { this.slide7(v); }
  private slide7(v: number): void { this.slide8(v); }
  private slide8(v: number): void { this.slide9(v); }
  private slide9(v: number): void { this.slide10(v); }
  
  private slide10(v: number): void {
    this.sliderVal = v;
    this.service019.method019();
  }
  
  build() {
    Slider({ value: this.sliderVal, min: 0, max: 100 })
      .onChange(this.onSlide)
  }
}
