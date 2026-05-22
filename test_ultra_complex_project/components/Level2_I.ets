/**
 * Level2_I.ets - 二级组件I
 */

import { Service_011 } from '../services/Service_011';
import { Level3_I } from './Level3_I';

@Component
struct Level2_I {
  @State private rating: number = 0;
  
  private service011: Service_011 = new Service_011();
  
  private onRatingChange = (value: number): void => {
    this.rating1(value);
  }
  
  private rating1(v: number): void { this.rating2(v); }
  private rating2(v: number): void { this.rating3(v); }
  private rating3(v: number): void { this.rating4(v); }
  private rating4(v: number): void { this.rating5(v); }
  private rating5(v: number): void { this.rating6(v); }
  private rating6(v: number): void { this.rating7(v); }
  private rating7(v: number): void { this.rating8(v); }
  private rating8(v: number): void { this.rating9(v); }
  private rating9(v: number): void { this.rating10(v); }
  
  private rating10(v: number): void {
    this.rating = v;
    this.service011.method011();
  }
  
  build() {
    Column() {
      Level3_I()
      Rating({ rating: this.rating })
        .onChange(this.onRatingChange)
    }
  }
}
