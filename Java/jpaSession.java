
@Component
@Slf4j
public class CtxUtil implements ApplicationContextAware {

    private static ApplicationContext applicationContext;

    public static ApplicationContext getApplicationContext() {
            return applicationContext;
        }

    @Override
    public void setApplicationContext(ApplicationContext ctx) throws BeansException {
            applicationContext = ctx;
            log.info("init ctx ok");
        }

    public static <T> T getBean(Class<T> clazz) {
            return applicationContext.getBean(clazz);
        }

    public static <T> T getBean(String name, Class<T> clazz) {
            return applicationContext.getBean(name, clazz);
        }
}


public class TransactionSupplier<T> implements Supplier<T> {
  private Supplier<T> supplier;

  private TransactionSupplier() {
    }

  public static <T> TransactionSupplier of(Supplier<T> supplier) {
      TransactionSupplier<T> transactionSupplier = new TransactionSupplier<T>();
      transactionSupplier.supplier = supplier;
      return transactionSupplier;
    }

  @Override
  public T get() {
      EntityManagerFactory entityManagerFactory = CtxUtil.getApplicationContext().getBean(EntityManagerFactory.class);
      EntityManager entityManager = entityManagerFactory.createEntityManager();
      EntityManagerHolder entityManagerHolder = new EntityManagerHolder(entityManager);
      TransactionSynchronizationManager.bindResource(entityManagerFactory, entityManagerHolder);
      try{
            return this.supplier.get();
          }finally {
                TransactionSynchronizationManager.unbindResource(entityManagerFactory);
                EntityManagerFactoryUtils.closeEntityManager(entityManager);
              }
    }
}



workExecutor.submit(() -> {
            val supplier = TransactionSupplier.of(() -> updateDatasourceScore(datasourceDo));
            supplier.get();
        });
