import { NestFactory } from '@nestjs/core';
import { Logger, ValidationPipe } from '@nestjs/common';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import cookieParser from 'cookie-parser';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.setGlobalPrefix('api/v1');
  const corsOrigins = process.env.CORS_ORIGINS
    ? process.env.CORS_ORIGINS.split(',').map((origin) => origin.trim())
    : ['http://localhost:3001', 'http://localhost:3000'];

  app.enableCors({
    origin: corsOrigins,
    credentials: true,
  });
  app.use(cookieParser());
  app.useGlobalPipes(new ValidationPipe({ transform: true, whitelist: true }));

  const config = new DocumentBuilder()
    .setTitle('Agente de Vendas API')
    .setDescription('REST API for the AI Sales Agent CRM')
    .setVersion('1.0')
    .addBearerAuth()
    .build();
  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api/docs', app, document);

  // Graceful shutdown
  app.enableShutdownHooks();

  const port = process.env.NESTJS_PORT || 4000;
  await app.listen(port);
  Logger.log(`✅ NestJS running on port ${port}`, 'Bootstrap');
}
bootstrap();
