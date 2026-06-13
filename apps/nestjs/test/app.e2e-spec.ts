import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication, ValidationPipe } from '@nestjs/common';
import request from 'supertest';
import cookieParser from 'cookie-parser';
import { AppModule } from '../src/app.module';

describe('Agente Vendas API (e2e)', () => {
  let app: INestApplication;
  let accessToken: string;

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    app.use(cookieParser());
    app.setGlobalPrefix('api/v1');
    app.useGlobalPipes(new ValidationPipe({ transform: true, whitelist: true }));
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  describe('Auth', () => {
    const testEmail = `e2e-${Date.now()}@test.com`;
    it('POST /api/v1/auth/register - should register a new user', async () => {
      const res = await request(app.getHttpServer())
        .post('/api/v1/auth/register')
        .send({ email: testEmail, password: '123456', name: 'Test' });
      expect(res.status).toBe(201);
      expect(res.body).toEqual({ ok: true });
      // Token is set as HTTP-only cookie; extract it for subsequent requests
      const cookies = ([] as string[]).concat(res.headers['set-cookie'] ?? []);
      const tokenCookie = cookies.find((c: string) => c.startsWith('token='));
      expect(tokenCookie).toBeDefined();
      accessToken = tokenCookie!.split(';')[0].replace('token=', '');
    });

    it('POST /api/v1/auth/register - should reject duplicate email', async () => {
      const res = await request(app.getHttpServer())
        .post('/api/v1/auth/register')
        .send({ email: testEmail, password: '123456' });
      expect(res.status).toBe(409);
      expect(res.body.message).toContain('already registered');
    });

    it('POST /api/v1/auth/login - should login', async () => {
      const res = await request(app.getHttpServer())
        .post('/api/v1/auth/login')
        .send({ email: testEmail, password: '123456' });
      expect(res.status).toBe(201);
      expect(res.body).toEqual({ ok: true });
      // Extract fresh token from login
      const cookies = ([] as string[]).concat(res.headers['set-cookie'] ?? []);
      const tokenCookie = cookies.find((c: string) => c.startsWith('token='));
      expect(tokenCookie).toBeDefined();
      accessToken = tokenCookie!.split(';')[0].replace('token=', '');
    });

    it('POST /api/v1/auth/login - should reject wrong password', async () => {
      const res = await request(app.getHttpServer())
        .post('/api/v1/auth/login')
        .send({ email: testEmail, password: 'wrong' });
      expect(res.status).toBe(401);
    });
  });

  describe('Conversations', () => {
    it('GET /api/v1/conversations - should require auth', async () => {
      const res = await request(app.getHttpServer()).get('/api/v1/conversations');
      expect(res.status).toBe(401);
    });

    it('GET /api/v1/conversations - should return list', async () => {
      const res = await request(app.getHttpServer())
        .get('/api/v1/conversations')
        .set('Authorization', `Bearer ${accessToken}`);
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
    });
  });

  describe('Products', () => {
    let productId: string;

    it('POST /api/v1/products - should create product', async () => {
      const res = await request(app.getHttpServer())
        .post('/api/v1/products')
        .set('Authorization', `Bearer ${accessToken}`)
        .send({ name: 'Test Product', price: 29.9, category: 'test', stock: 10 });
      expect(res.status).toBe(201);
      expect(res.body).toHaveProperty('id');
      productId = res.body.id;
    });

    it('GET /api/v1/products - should list products', async () => {
      const res = await request(app.getHttpServer())
        .get('/api/v1/products')
        .set('Authorization', `Bearer ${accessToken}`);
      expect(res.status).toBe(200);
      expect(res.body.products.length).toBeGreaterThan(0);
    });

    it('PUT /api/v1/products/:id - should update product', async () => {
      const res = await request(app.getHttpServer())
        .put(`/api/v1/products/${productId}`)
        .set('Authorization', `Bearer ${accessToken}`)
        .send({ price: 19.9 });
      expect(res.status).toBe(200);
    });
  });
});
