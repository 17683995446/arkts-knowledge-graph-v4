/**
 * 产品模型 - 定义产品数据结构
 */

// 产品类别枚举
enum ProductCategory {
  ELECTRONICS = 'electronics',
  CLOTHING = 'clothing',
  FOOD = 'food',
  HOME = 'home',
  SPORTS = 'sports',
  BOOKS = 'books',
  BEAUTY = 'beauty',
  TOYS = 'toys'
}

// 产品状态枚举
enum ProductStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  OUT_OF_STOCK = 'out_of_stock',
  DISCONTINUED = 'discontinued'
}

// 产品图片
interface ProductImage {
  id: string;
  url: string;
  alt?: string;
  isPrimary?: boolean;
}

// 产品规格
interface ProductSpecification {
  name: string;
  value: string;
}

// 产品变体
interface ProductVariant {
  id: string;
  sku: string;
  name: string;
  price: number;
  stock: number;
  attributes: Record<string, string>;
}

// 产品评价
interface ProductReview {
  id: string;
  userId: string;
  rating: number;
  comment?: string;
  createdAt: Date;
}

// 产品模型
interface Product {
  id: string;
  name: string;
  description?: string;
  sku: string;
  price: number;
  originalPrice?: number;
  category: ProductCategory;
  status: ProductStatus;
  stock: number;
  images: ProductImage[];
  specifications?: ProductSpecification[];
  variants?: ProductVariant[];
  reviews?: ProductReview[];
  tags?: string[];
  weight?: number;
  dimensions?: {
    length: number;
    width: number;
    height: number;
  };
  createdAt: Date;
  updatedAt: Date;
}

// 产品构建器
class ProductBuilder {
  private product: Partial<Product> = {
    status: ProductStatus.ACTIVE,
    stock: 0,
    images: [],
    specifications: [],
    variants: [],
    reviews: [],
    tags: [],
    createdAt: new Date(),
    updatedAt: new Date()
  };

  setId(id: string): ProductBuilder {
    this.product.id = id;
    return this;
  }

  setName(name: string): ProductBuilder {
    this.product.name = name;
    return this;
  }

  setDescription(description: string): ProductBuilder {
    this.product.description = description;
    return this;
  }

  setSku(sku: string): ProductBuilder {
    this.product.sku = sku;
    return this;
  }

  setPrice(price: number): ProductBuilder {
    this.product.price = price;
    return this;
  }

  setOriginalPrice(price: number): ProductBuilder {
    this.product.originalPrice = price;
    return this;
  }

  setCategory(category: ProductCategory): ProductBuilder {
    this.product.category = category;
    return this;
  }

  setStatus(status: ProductStatus): ProductBuilder {
    this.product.status = status;
    return this;
  }

  setStock(stock: number): ProductBuilder {
    this.product.stock = stock;
    return this;
  }

  addImage(image: ProductImage): ProductBuilder {
    if (!this.product.images) {
      this.product.images = [];
    }
    this.product.images.push(image);
    return this;
  }

  addSpecification(spec: ProductSpecification): ProductBuilder {
    if (!this.product.specifications) {
      this.product.specifications = [];
    }
    this.product.specifications.push(spec);
    return this;
  }

  addVariant(variant: ProductVariant): ProductBuilder {
    if (!this.product.variants) {
      this.product.variants = [];
    }
    this.product.variants.push(variant);
    return this;
  }

  addReview(review: ProductReview): ProductBuilder {
    if (!this.product.reviews) {
      this.product.reviews = [];
    }
    this.product.reviews.push(review);
    return this;
  }

  addTag(tag: string): ProductBuilder {
    if (!this.product.tags) {
      this.product.tags = [];
    }
    this.product.tags.push(tag);
    return this;
  }

  setWeight(weight: number): ProductBuilder {
    this.product.weight = weight;
    return this;
  }

  setDimensions(length: number, width: number, height: number): ProductBuilder {
    this.product.dimensions = { length, width, height };
    return this;
  }

  build(): Product {
    if (!this.product.id || !this.product.name || !this.product.sku) {
      throw new Error('Product must have id, name and sku');
    }
    if (this.product.price === undefined || this.product.price < 0) {
      throw new Error('Product must have a valid price');
    }
    
    return this.product as Product;
  }
}

// 产品计算器
class ProductCalculator {
  // 计算折扣率
  static calculateDiscountRate(product: Product): number {
    if (!product.originalPrice || product.originalPrice <= 0) {
      return 0;
    }
    return ((product.originalPrice - product.price) / product.originalPrice) * 100;
  }

  // 计算平均评分
  static calculateAverageRating(product: Product): number {
    if (!product.reviews || product.reviews.length === 0) {
      return 0;
    }
    const sum = product.reviews.reduce((acc, review) => acc + review.rating, 0);
    return sum / product.reviews.length;
  }

  // 计算总库存（包括变体）
  static calculateTotalStock(product: Product): number {
    let total = product.stock;
    if (product.variants) {
      total += product.variants.reduce((sum, variant) => sum + variant.stock, 0);
    }
    return total;
  }

  // 计算体积
  static calculateVolume(product: Product): number {
    if (!product.dimensions) return 0;
    return product.dimensions.length * product.dimensions.width * product.dimensions.height;
  }
}

// 产品验证器
class ProductValidator {
  // 验证SKU格式
  static validateSku(sku: string): boolean {
    return /^[A-Z0-9-]+$/.test(sku) && sku.length >= 3;
  }

  // 验证价格
  static validatePrice(price: number): boolean {
    return price >= 0 && !isNaN(price);
  }

  // 验证库存
  static validateStock(stock: number): boolean {
    return Number.isInteger(stock) && stock >= 0;
  }

  // 验证产品
  static validate(product: Partial<Product>): {
    valid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];

    if (!product.name || product.name.length < 2) {
      errors.push('Product name must be at least 2 characters');
    }

    if (!product.sku || !this.validateSku(product.sku)) {
      errors.push('Invalid SKU format');
    }

    if (product.price === undefined || !this.validatePrice(product.price)) {
      errors.push('Invalid price');
    }

    if (product.stock !== undefined && !this.validateStock(product.stock)) {
      errors.push('Invalid stock quantity');
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }
}

// 产品筛选器
class ProductFilter {
  private filters: ((product: Product) => boolean)[] = [];

  byCategory(category: ProductCategory): ProductFilter {
    this.filters.push(p => p.category === category);
    return this;
  }

  byStatus(status: ProductStatus): ProductFilter {
    this.filters.push(p => p.status === status);
    return this;
  }

  byPriceRange(min: number, max: number): ProductFilter {
    this.filters.push(p => p.price >= min && p.price <= max);
    return this;
  }

  byMinStock(minStock: number): ProductFilter {
    this.filters.push(p => p.stock >= minStock);
    return this;
  }

  byTag(tag: string): ProductFilter {
    this.filters.push(p => p.tags?.includes(tag) || false);
    return this;
  }

  apply(products: Product[]): Product[] {
    return products.filter(product =>
      this.filters.every(filter => filter(product))
    );
  }
}

// 产品排序器
class ProductSorter {
  static byPrice(products: Product[], ascending: boolean = true): Product[] {
    return [...products].sort((a, b) =>
      ascending ? a.price - b.price : b.price - a.price
    );
  }

  static byName(products: Product[], ascending: boolean = true): Product[] {
    return [...products].sort((a, b) =>
      ascending
        ? a.name.localeCompare(b.name)
        : b.name.localeCompare(a.name)
    );
  }

  static byDate(products: Product[], ascending: boolean = false): Product[] {
    return [...products].sort((a, b) => {
      const timeA = a.createdAt.getTime();
      const timeB = b.createdAt.getTime();
      return ascending ? timeA - timeB : timeB - timeA;
    });
  }

  static byRating(products: Product[], ascending: boolean = false): Product[] {
    return [...products].sort((a, b) => {
      const ratingA = ProductCalculator.calculateAverageRating(a);
      const ratingB = ProductCalculator.calculateAverageRating(b);
      return ascending ? ratingA - ratingB : ratingB - ratingA;
    });
  }
}

export {
  ProductCategory,
  ProductStatus,
  ProductBuilder,
  ProductCalculator,
  ProductValidator,
  ProductFilter,
  ProductSorter
};
export type {
  Product,
  ProductImage,
  ProductSpecification,
  ProductVariant,
  ProductReview
};
