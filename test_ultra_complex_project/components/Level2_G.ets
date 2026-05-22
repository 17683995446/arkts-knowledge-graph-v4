/**
 * Level2_G.ets - 二级组件G
 */

import { Service_009 } from '../services/Service_009';
import { Level3_G } from './Level3_G';

@Component
struct Level2_G {
  @State private selectedIndex: number = -1;
  
  private service009: Service_009 = new Service_009();
  
  private selectItem = (index: number): void => {
    this.select1(index);
  }
  
  private select1(i: number): void { this.select2(i); }
  private select2(i: number): void { this.select3(i); }
  private select3(i: number): void { this.select4(i); }
  private select4(i: number): void { this.select5(i); }
  private select5(i: number): void { this.select6(i); }
  private select6(i: number): void { this.select7(i); }
  private select7(i: number): void { this.select8(i); }
  private select8(i: number): void { this.select9(i); }
  private select9(i: number): void { this.select10(i); }
  
  private select10(i: number): void {
    this.selectedIndex = i;
    this.service009.method009();
  }
  
  build() {
    Column() {
      Level3_G()
      Select([{ value: 'A' }, { value: 'B' }])
        .onSelect(this.selectItem)
    }
  }
}
